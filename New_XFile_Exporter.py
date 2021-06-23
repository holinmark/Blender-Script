import bpy, mathutils, math, copy, os
from collections import deque

class cUserException(Exception):
    def __init__(self, error_string, line_number):
        self.error = error_string
        self.line = line_number
        
    def __str__(self):
        return self.error + "\n" + str(self.line) + "\n"

def RemoveWhiteSpace(s):
    if type(s).__name__ == 'str':
        tmp = ''
        for i in range(len(s)):
            if s[i] == ' ':
                tmp += '_'
            else:
                tmp += s[i]
        return tmp

def IndentFormat(hfile, indent, s, a):
    arg = 0
    for i in range(0, len(s)):
        if s[i] == '{':
            if (i + 1) != len(s):
                if s[i + 1] == '}':
                    arg += 1
    if arg != len(a):
        raise(cUserException("Arguments different", 32))
    file_output = ''
    index = 0
    for i in range(0, len(s)):
        if s[i] == '-':
            for i in range(0, indent):
                file_output += '  '
        elif s[i] == '+':
            indent += 1
        elif s[i] == '{':
            if len(s) == (i + 1):
                file_output += '{'
            else:
                if s[i + 1] == '}':
                    file_output += a[index]
                    index += 1
                else:
                    file_output += '{'
        else:
            if s[i] == '}':
                if i != 0:
                    if s[i - 1] != '{':
                        file_output += s[i]
                else:
                    file_output += s[i]
            else:
                file_output += s[i]
    hfile.write(file_output)
    return True

def Indent(hfile, indent, title = None):
    s = ''
    for i in range(0, indent):
        s += '  '
    if title != None:
        s += title
    hfile.write(s)

def ExtractMatrixToFile(hfile, indent, matrix, lhc = False, title = None):
    args = []
    if title == None:
        title = "Matrix4x4 {"
        args.append(title)
    else:
        args.append(title)
    format_string = "-{} "
    IndentFormat(hfile, indent, format_string, args)
    seperator = deque()
    for i in range(1, 4):
        seperator.append(", ")
    seperator.append(";")
    for row in matrix.transposed():
        format_string = "{}{} {}{} {}{} {}{}"
        args = [str(row.x), ",", str(row.y), ",", str(row.z), ",", str(row.w), seperator.popleft()]
        IndentFormat(hfile, indent, format_string, args)
    s = ""
    if title == "Matrix4x4 {":
        s = " }\n"
    else: #FrameTransformMatrix
        s = "; }\n"
    hfile.write(s)
    del args, format_string, seperator, s

def GetLeftHandCoordinateMatrix(matrix):
    l, r, s = matrix.decompose()
    if type(r).__name__ == "Quaternion":
        r = r.to_euler()
    if lhc:
        l.z *= -1
        r.z *= -1
    r = r.to_quaternion()
    lmat = mathutils.Matrix.Translation(l)
    rmat = r.to_matrix().to_4x4()
    smat = mathutils.Matrix.Scale(s[0], 4, (1, 0, 0)) * mathutils.Matrix.Scale(s[1], 4, (0, 1, 0)) * mathutils.Matrix.Scale(s[2], 4, (0, 0, 1))
    matrix = lmat * rmat * smat
    return matrix

def ExtractMatrices(hfile, indent, matrix, lhc):
    for m in matrix:
        ExtractMatrixToFile(hfile, indent, m)

def ExtractTextureCoordinateToFile(hfile, indent, obj):
    if len(obj.data.uv_layers) == 0:
        return
    format_string = "-{}\n--{}\n"
    uv_layer = obj.data.uv_layers.active
    args = ["MeshTextureCoords {", str(len(uv_layer.data)) + ";"]
    IndentFormat(hfile, indent, format_string, args)
    format_string = ""
    args.clear()
    sep1 = deque()
    for i in range(len(uv_layer.data) - 1):
        sep1.append(',')
    sep1.append(';')
    for p in obj.data.polygons:
        for loop in range(p.loop_start, p.loop_total + p.loop_start):
            u = uv_layer.data[loop].uv[0]
            v = 1 - uv_layer.data[loop].uv[1]
            format_string += "--{} {}\n"
            args += [str(u) + ';', str(v) + ';' + sep1.popleft()]
    IndentFormat(hfile, indent, format_string, args)
    Indent(hfile, indent, "} // End of MeshTextureCoords\n")
    del format_string, args, sep1, uv_layer

def ExtractMaterials(hfile, indent, obj):
    s = "MeshMaterialList {\n"
    Indent(hfile, indent, s)
    indent += 1
    s = "{}{}\n".format(len(obj.data.materials), ';')
    Indent(hfile, indent, s)
    s = "{}{}\n".format(len(obj.data.polygons), ';')
    Indent(hfile, indent, s)
    for i, p in enumerate(obj.data.polygons):
        if i != (len(obj.data.polygons) - 1):
            s = "{}{}\n".format(p.material_index, ',')
            Indent(hfile, indent, s)
        else:
            s = str(obj.data.polygons[len(obj.data.polygons) - 1].material_index) + ';\n'
            Indent(hfile, indent, s)
    for m in obj.data.materials:
        s = "Material " + RemoveWhiteSpace(m.name) + " {\n"
        Indent(hfile, indent, s)
        indent += 1
        c = m.diffuse_color
        s = "{}; {}; {}; {};;\n".format(str(c[0]), str(c[1]), str(c[2]), m.alpha)
        Indent(hfile, indent, s)
        c = m.specular_hardness
        s = "{}{}".format(str(c), ';\n')
        Indent(hfile, indent, s)
        c = m.specular_color
        s = "{}; {}; {};;\n".format(str(c[0]), str(c[1]), str(c[2]))
        Indent(hfile, indent, s)
        s = "0.0; 0.0; 0.0;;\n"
        Indent(hfile, indent, s)    
        if m.active_texture != None:
            if m.active_texture.type == "IMAGE":
                s = "TextureFilename {\n"
                Indent(hfile, indent, s)
                p, f = path.split(m.active_texture.image.filepath)
                if len(f) > 0:
                    s = "{}{}{}\n".format("\"", f, "\";")
                else:
                    s = "{}{}{}\n".format("\"", m.active_texture.image.filepath, "\";")
                Indent(hfile, indent + 1, s)
                s = "{}\n".format('} // End of TextureFileName')
                Indent(hfile, indent, s)
        indent -= 1
        s = "{} {}\n".format("} // End of Material", RemoveWhiteSpace(m.name))
        Indent(hfile, indent, s)
    indent -= 1
    s = "} // End of MeshMaterialList\n"
    Indent(hfile, indent, s)

def GetMatrixOffset(hfile, indent, arm, bone_name):
    # Matrix offset needs more work.  I'm pretty sure it's incorrect.
    matrixoffset = mathutils.Matrix.Identity(4)
    if bone_name not in arm.data.bones:
        raise(cUserException("In GetMatrixOffset ", bone_name + " does not exist.", 187))
    bone = arm.data.bones[bone_name]
    arm_loc, arm_rotation, arm_scale = bone.matrix_local.decompose()
    if len(arm.children) > 0:
        child_loc, child_rot, child_scale = arm.children[0].matrix_world.decompose()
        diff_loc = (-1 * child_loc) + arm_loc + bone.head_local
        matrixoffset = matrixoffset * mathutils.Matrix.Translation(diff_loc) * child_rot.to_matrix().to_4x4()
        scale = mathutils.Matrix.Scale(child_scale.x, 4, (1.0, 0, 0)) * mathutils.Matrix.Scale(child_scale.y, 4, (0, 1.0, 0)) * mathutils.Matrix.Scale(child_scale.z, 4, (0, 0, 1.0))
        matrixoffset = matrixoffset * scale
    indent += 1
    ExtractMatrixToFile(hfile, indent, matrixoffset)
    indent -= 1

def ExtractWeights(hfile, indent, obj):
    s = "\n// mesh weights go here\n\n"
    hfile.write(s)
    if obj.parent == None:
        return
    if obj.parent.type != "ARMATURE":
        return
    weights = dict()
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group not in weights.keys():
                weights[g.group] = [(v.index, g.weight)]
            else:
                weights[g.group] += [(v.index, g.weight)]
    sep = deque()
    master = deque()
    for group in weights.keys():
        format_string = "-{}\n--{}{}{};\n"
        args = ["SkinWeights {", "\"", obj.vertex_groups[group].name, "\""]
        IndentFormat(hfile, indent, format_string, args)
        indices = []
        weight = []
        format_string = "--{};\n"
        for i in range(len(weights[group]) - 1):
            sep.append(',')
        sep.append(';')
        master = sep.copy()
        args = [str(len(weights[group]))]
        IndentFormat(hfile, indent, format_string, args)
        for i, w in weights[group]:
            indices.append(i)
            weight.append(w)
        format_string = ""
        args = []
        for i in indices:
            format_string += "--{}{}\n"
            args += [str(i), sep.popleft()]
        IndentFormat(hfile, indent, format_string, args)
        format_string = ""
        args = []
        sep = master.copy()
        for w in weight:
            format_string += "--{}{}\n"
            args += [str(w), sep.popleft()]
        IndentFormat(hfile, indent, format_string, args)
        if obj.parent != None:
            GetMatrixOffset(hfile, indent, bpy.context.scene.objects[obj.parent.name], obj.vertex_groups[group].name)
        else:
            print(obj.name, "no parent.")
        format_string = "-{} {}\n"
        args = ["}", "// End of SkinWeights"]
        IndentFormat(hfile, indent, format_string, args)
        sep.clear()
        master.clear()
    del sep, master, weights, args, format_string

def ExtractVerticesToFile(hfile, indent, obj, lhc):
    if type(obj).__name__ != "Object":
        return False
    v = obj.data.vertices
    sep = deque()
    for i in range(len(v) - 1):
        sep.append(',')
    sep.append(';')
    format_string = ''
    args = []
    for i in range(0, len(v)):
        format_string += '-{}; {}; {};' + sep.popleft() + '\n'
        args.extend([str(v[i].co.x), str(v[i].co.y), str(v[i].co.z)])
    IndentFormat(hfile, indent, format_string, args)
    del format_string, args, sep, v

def ExtractMeshPolygons(hfile, indent, obj, lhc):
    format_string = '-{};\n'
    args = [str(len(obj.data.polygons))]
    normal_string = '-{} {}\n--{}{}\n'
    normal_args = ["MeshNormals", '{', str(len(obj.data.polygons)), ';']
    face_string = '--{};\n'
    face_args = [str(len(obj.data.polygons))]
    sep = deque()
    sep2 = deque()
    normal_sep = deque()
    face_sep = deque()
    face_sep2 = deque()
    for i in range(len(obj.data.polygons) - 1):
        sep2.append(',')
    sep2.append(';')
    normal_sep = sep2.copy()
    face_sep2 = sep2.copy()
    for index, polygon in enumerate(obj.data.polygons):
        for i in range(polygon.loop_total - 1):
            sep.append(', ')
        sep.append(';')
        face_sep = sep.copy()
        format_string += '-{}; '
        args.append(str(polygon.loop_total))
        normal_string += '--{}; {}; {};' + normal_sep.popleft() + '\n'
        normal_args.extend([str(polygon.normal.x), str(polygon.normal.y), str(polygon.normal.z)])
        face_string += '--{}; '
        face_args.append(str(polygon.loop_total))
        for loop in range(polygon.loop_start, polygon.loop_total + polygon.loop_start):
            vi = obj.data.loops[loop].vertex_index
            format_string += '{}' + sep.popleft()
            args.append(str(vi))
            face_string += '{}' + face_sep.popleft()
            face_args.append(str(index))
        format_string += sep2.popleft() + '\n'
        face_string += face_sep2.popleft() + '\n'
    IndentFormat(hfile, indent, format_string, args)
    face_string += '-{} {}\n'
    face_args.extend(['}', '// End of MeshNormals'])
    IndentFormat(hfile, indent, normal_string, normal_args)
    IndentFormat(hfile, indent, face_string, face_args)
    del normal_string, normal_args
    del format_string, args
    del sep, sep2, normal_sep
    del face_string, face_args

def ExtractMeshInfoToFile(hfile, obj, matrix, lhc = False):
    if type(hfile).__name__ != "TextIOWrapper":
        return False
    if type(obj).__name__ != "Object":
        return False
    if type(matrix).__name__ != "list":
        return False
    indent = 0
    format_string = "-{} {} {}\n+-{}{}\n"
    name = RemoveWhiteSpace(obj.name)
    print("Extracting mesh", obj.name)
    args = ["Mesh", RemoveWhiteSpace(obj.name), "{", str(len(obj.data.vertices)), ";"]
    IndentFormat(hfile, indent, format_string, args)
    indent += 1
    ExtractVerticesToFile(hfile, indent, obj, lhc)
    del format_string
    args.clear()
    ExtractMeshPolygons(hfile, indent, obj, lhc)
    ExtractTextureCoordinateToFile(hfile, indent, obj)
    """
    if len(obj.data.uv_textures) > 0:
        for index, layer in enumerate(obj.data.uv_textures):
            if layer.active == True:
                uv_layer_active_index = index
                ExtractTextureCoordinateToFile(hfile, indent, obj)
                break
        del index, layer, uv_layer_active_index
    if len(obj.material_slots) > 0:
        ExtractMaterials(hfile, indent, obj)
    """
    if len(obj.vertex_groups) > 0 and obj.parent != None:
        if obj.parent.select:
            ExtractWeights(hfile, indent, obj)
    ExtractMatrices(hfile, indent, matrix, lhc)
    format_string = "} // End of mesh " + name + "\n\n"
    hfile.write(format_string)
    del format_string
    return True

def ExtractArmaturesInfoToFile(hfile, armatures, lhc = False):
    if type(hfile).__name__ != "TextIOWrapper":
        return False
    if type(armatures).__name__ != "deque":
        return False
    if len(armatures) <= 0:
        return True
    bone_stack = list()
    indent = 0
    for currarmature in reversed(armatures):
        name = RemoveWhiteSpace(currarmature)
        print("Extracting armature", currarmature)
        Indent(hfile, indent, "\nFrame " + name + " {\n")
        a = bpy.context.scene.objects[currarmature]
        if a.children != None:
            for child in a.children:
                Indent(hfile, indent, "{ " + child.name + " }\n")
            if a.parent != None:
                matrix = a.matrix_local.copy()
            else:
                matrix = a.matrix_world.copy()
        ExtractMatrixToFile(hfile, indent + 1, matrix, lhc, "FrameTransformMatrix {")
        #first bone in armature has no parent
        for bone in a.data.bones:
            if bone.parent == None:
                bone_stack.append((indent + 1, bone.name, None))
        while len(bone_stack) > 0:
            top = bone_stack.pop()
            if len(top) == 3:
                indent, currbone, parent = top
            else:
                indent, s = top
                Indent(hfile, indent, s)
                continue
            Indent(hfile, indent, 'Frame ' + currbone + ' {\n')
            s = "Vector { " + str(0) + "; " + str(a.data.bones[currbone].length) + "; " + str(0) + "; }\n"
            Indent(hfile, indent + 1, s)
            ExtractMatrixToFile(hfile, indent + 1, a.data.bones[currbone].matrix_local.copy(), lhc, "FrameTransformMatrix {")
            if len(a.data.bones[currbone].children) > 0:
                bone_stack.append((indent, '} // End of ' + currbone + '\n'))
                for child in a.data.bones[currbone].children:
                    bone_stack.append((indent + 1, child.name, child.parent.name))
                continue
            Indent(hfile, indent, '} // End of ' + currbone + '\n')
        indent -= 1
        Indent(hfile, indent, '} // End of ' + currarmature + '\n')
        print(currarmature, "extracted.")
    hfile.write("\n")

def GetRotate(obj):
    if obj.rotation_mode == 'QUATERNION':
        e = obj.rotation_quaternion
        return ("{}; {}, {}, {}, {};", [str(len(e)), str(e.w), str(e.x), str(e.y), str(e.z)])
    else:
        e = obj.rotation_euler.copy()
        return ("{}; {}, {}, {};", [str(len(e)), str(e.x), str(e.y), str(e.z)])

def GetQuaternionRotation(obj, hfile, indent):
    r = obj.rotation_quaternion

def GetEulerRotation(obj, hfile, indent):
    r = obj.rotation_euler

def GetScale(obj):
    return ("{}; {}, {}, {};", [str(len(obj.scale)), str(obj.scale[0]), str(obj.scale[1]), str(obj.scale[2])])

def GetTranslate(obj):
    return ("{}; {}, {}, {};", [str(len(obj.location)), str(obj.location[0]), str(obj.location[1]), str(obj.location[2])])

def ExtractAnimationDataPerFrames(hfile, indent, time, TypeOfTransform, sep, name):
    format_string = "-{} {}\n+-{}{}\n-{}{}\n"
    args = ["AnimationKey", "{", str(type[0]), ";", str(time[1] - time[0]), ";"]
    IndentFormat(hfile, indent, format_string, args)
    obj = bpy.context.scene.objects[name]
    indent += 1
    format_string = ""
    args.clear()
    for frame in range(time[0], time[1]):
        bpy.context.scene.frame_set(frame)
        args.append(str(frame))
        r = TypeOfTransform[1](obj) #function call
        format_string += '-{}; ' + r[0] + ';' + sep.popleft() + '\n'
        args.extend(r[1])
    IndentFormat(hfile, indent, format_string, args)
    indent -= 1
    format_string = "-{} {}\n"
    args.clear()
    args = ["}", "// End of AnimationKey"]
    IndentFormat(hfile, indent, format_string, args)

def ExtractMarkers(timelines):
    if len(bpy.context.scene.timeline_markers) > 0:
        for m in bpy.context.scene.timeline_markers:
            if m.select:
                timelines.append((m.frame, m.name))
    else:
        if bpy.context.scene.frame_start == bpy.context.scene.frame_end:
            return
        timelines.extend([(bpy.context.scene.frame_start, "Start"), (bpy.context.scene.frame_end, "End")])
    timelines.sort(key=lambda frame : frame[0])
    if timelines[len(timelines) - 1][0] != bpy.context.scene.frame_end:
        timelines.append((bpy.context.scene.frame_end, "End"))

def GetMeshAnimation(hfile, indent, time_slot, obj):
    format_string = ''
    args = []
    sep1 = deque()
    sep2 = deque()
    total = time_slot[1][0] - time_slot[0][0]
    for i in range(total - 1):
        sep1.append(',')
    sep1.append(';')
    sep2 = copy.copy(sep1)
    format_string += "-{} {} {}\n--{}{}{}\n"
    args.extend(["Animation", time_slot[0][1], '{', '{', obj.name, '}'])
    IndentFormat(hfile, indent, format_string, args)
    sep2 = copy.copy(sep1)
    ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (1, GetScale), sep2, obj.name)
    sep2 = copy.copy(sep1)
    ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (2, GetTranslate), sep2, obj.name)
    sep2 = copy.copy(sep1)
    ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (0, GetRotate), sep2, obj.name)
    del format_string
    format_string = '-{}\n'
    args.clear()
    args.extend(["} // End of Animation"])
    IndentFormat(hfile, indent, format_string, args)
    del sep1, sep2, format_string, args, total

def GetArmatureAnimation(hfile, indent, time_slot, obj):
    sep = deque()
    sep1 = deque()
    for bone in obj.pose.bones:
        format_string = '-{} {} {}\n--{}{}{}\n'
        args = ["Animation", time_slot[0][1], '{', '{', bone.name, '}']
        IndentFormat(hfile, indent, format_string, args)
        indent += 1
        format_string = "-{}\n--{}; {}\n"
        args = ["AnimationKey {", str(0), "// Rotation"]
        IndentFormat(hfile, indent, format_string, args)
        format_string = ""
        args.clear()
        count = 0
        r = None
        for i in range(time_slot[0][0], time_slot[1][0]):
            sep.append(',')
            sep1.append(',')
        sep.append(';')
        sep1.append(';')
        for frame in range(time_slot[0][0], time_slot[1][0] + 1):
            count += 1
        IndentFormat(hfile, indent, "--{};\n", [str(count)])
        bpy.context.scene.frame_set(time_slot[0][0])
        if bone.rotation_mode == "QUATERNION":
            IndentFormat(hfile, indent, "--{}--{}", ["// Quaternion rotation wxyz\n", "// local bone coordinate axis\n"])
        elif bone.rotataion_mode == "XYZ":
            IndentFormat(hfile, indent, "--{}--{}", ["// Euler rotation xyz\n", "// local bone coordinate axis\n"])
        for frame in range(time_slot[0][0], time_slot[1][0] + 1):
            bpy.context.scene.frame_set(frame)
            if bone.rotation_mode == "QUATERNION":
                r = bone.rotation_quaternion
                format_string = "--{}; {}; {}, {}, {}, {};;{}\n"
                args = [str(frame), str(len(r)), str(r.w), str(r.x), str(r.y), str(r.z), sep.popleft()]
            elif bone.rotation_mode == "XYZ":
                r = bon.rotation_euler
                format_string = "--{}; {}; {}, {}, {};;{}\n"
                args = [str(frame), str(len(r)), str(r.x), str(r.y), str(r.z), sep.popleft()]
            IndentFormat(hfile, indent, format_string, args)
        format_string = '-{} {}\n'
        args.clear()
        args = ['}', "// End of AnimationKey"]
        IndentFormat(hfile, indent, format_string, args)
        format_string = '-{}\n--{}; {}\n'
        args = ["AnimationKey {", str(2), "// Location"]
        IndentFormat(hfile, indent, format_string, args)
        count = 0
        format_string = ""
        args.clear()
        for frame in range(time_slot[0][0], time_slot[1][0] + 1):
            bpy.context.scene.frame_set(frame)
            #l = bone.location
            l = bone.location
            format_string += "--{}; {}; {}, {}, {};;{}\n"
            args += [str(frame), str(len(l)), str(l.x), str(l.y), str(l.z), sep1.popleft()]
            count += 1
        IndentFormat(hfile, indent, "--{};\n", [str(count)])
        IndentFormat(hfile, indent, format_string, args)
        format_string = "-{}\n"
        args = ["} // End of AnimationKey"]
        IndentFormat(hfile, indent, format_string, args)
        indent -= 1
        format_string = "-{} {} {}\n"
        args = ['}', "// End of Animation", time_slot[0][1]]
        IndentFormat(hfile, indent, format_string, args)
    del format_string, args
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)

def Markers(hfile, indent, markers, animate_data):
    if len(animate_data["MESH"]) > 0:
        for mesh_name in animate_data["MESH"]:
            format_string = "{} {} {}\n"
            args = ["AnimationSet", mesh_name, '{']
            IndentFormat(hfile, indent, format_string, args)
            for index, marker in enumerate(markers):
                if index != (len(markers) - 1):
                    GetMeshAnimation(hfile, indent, (marker, markers[index + 1]), bpy.context.scene.objects[mesh_name])
            del format_string
            format_string = "{} {} {}\n\n"
            args.clear()
            args = ['}', "// End of AnimationSet", mesh_name]
            IndentFormat(hfile, indent, format_string, args)
    if len(animate_data["ARMATURE"]) > 0:
        for armature_name in animate_data["ARMATURE"]:
            format_string = "{} {} {}\n"
            args = ["AnimationSet", armature_name, '{']
            IndentFormat(hfile, indent, format_string, args)
            for index, marker in enumerate(markers):
                if index != (len(markers) - 1):
                    GetArmatureAnimation(hfile, indent, (marker, markers[index + 1]), bpy.context.scene.objects[armature_name])
            del format_string
            format_string = "{} {} {}\n\n"
            args.clear()
            args = ['}', "// End of AnimationSet", armature_name]
            IndentFormat(hfile, indent, format_string, args)
    del args, format_string

def ExtractAnimation(hfile, indent, armatures, mesh, lhc):
    markers = list()
    ExtractMarkers(markers)
    animate_data = dict()
    animate_data["ARMATURE"] = dict()
    animate_data["MESH"] = dict()
    for a in armatures:
        if bpy.context.scene.objects[a].animation_data != None:
            animate_data["ARMATURE"][a] = []
    for m in mesh:
        if bpy.context.scene.objects[m].animation_data != None:
            animate_data["MESH"][m] = []
    number_of_animation_data = 0
    for a in animate_data:
        number_of_animation_data += len(animate_data[a])
    if number_of_animation_data == 0:
        return
    sep = deque()
    format_string = "{} {}\n{};\n{} {}\n\n"
    args = ["AnimTicksPerSecond", "{", str(bpy.context.scene.render.fps), '}', "// End of AnimTicksPerSecond"]
    IndentFormat(hfile, indent, format_string, args)
    format_string = ''
    args.clear()
    Markers(hfile, indent, markers, animate_data)

def OutputToFile(filename, mesh, armatures, lhc):
    indent = 0
    with open(filename, "w") as hfile:
        s = "xof 0303txt 0032\n// Right hand coordinate system\n"
        if (len(mesh)) > 0:
            s += "// Face of polygons are counter clockwise\n"
            s += "// Number of meshes " + str(len(mesh)) + "\n"
        if (len(armatures)) > 0:
            s += "// Number of armatures " + str(len(armatures)) + "\n"
        for key in mesh.keys():
            s += "// Mesh " + key + '\n'
        s += '\n'
        hfile.write(s)
        for name in list(mesh):
            if ExtractMeshInfoToFile(hfile, bpy.context.scene.objects[name], mesh[name], lhc) == False:
                print("Could not extract", name)
            else:
                print(name, "extracted")
        if len(armatures) > 0:
            ExtractArmaturesInfoToFile(hfile, armatures, lhc)
        ExtractAnimation(hfile, indent + 1, armatures, mesh, lhc)

def GatherSceneDataThenOutputToFile279(file_name, lhc = False):
    mesh = dict()
    armatures = deque()
    for o in bpy.context.scene.objects:
        if o.select == False:
            continue
        # for meshes use dictionary.  Keys are names of the mesh object.  Values are the matrices and instances of the mesh object
        if o.type == "MESH":
            if o.mode != "OBJECT":
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    continue
            if o.parent != None:
                mat = o.matrix_basis.copy()
            else:
                mat = o.matrix_world.copy()
            if o.name not in mesh:
                mesh[o.name] = [mat]
            else:
                mesh[o.name].append(mat)
        # for armature use deque.  Inserting parent name of armature first then children name of armature after parent.
        elif o.type == "ARMATURE":
            if o.mode == 'EDIT':
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    continue
            if o.parent != None and o.parent.type == "ARMATURE":
                if o.parent.name not in armatures and o.parent.select:
                    armatures.append(o.parent.name)
            armatures.append(o.name)
        # Insert into mesh deque instance
        elif o.type == "EMPTY":
            if o.dupli_group != None:
                for obj in o.dupli_group.objects:
                    if obj.name in mesh:
                        mesh[obj.name].append(o.matrix_local.copy())
                    else:
                        mesh[obj.name] = [o.matrix_local.copy()]
    if len(armatures) == 0 and len(mesh) == 0:
        print("No mesh or armature selected")
        return False
    OutputToFile(file_name, mesh, armatures, lhc)
    return True

def GatherSceneDataThenOutputToFile280(file_name, lhc = False):
    meshes = dict()
    armatures = deque()
    for o in bpy.context.scene.objects:
        if not o.select_get():
            continue
        if o.type == "MESH":
            if o.mode != "OBJECT":
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    continue
            if o.parent != None:
                mat = o.matrix_basis.copy()
            else:
                mat = o.matrix_world.copy()
            if o.name not in meshes:
                meshes[o.name] = [mat]
            else:
                meshes[o.name].append(mat)
        # for armature use deque.  Inserting parent name of armature first then children name of armature after parent.
        elif o.type == "ARMATURE":
            if o.mode == 'EDIT':
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    continue
            if o.parent != None and o.parent.type == "ARMATURE":
                if o.parent.name not in armatures and o.parent.select:
                    armatures.append(o.parent.name)
            armatures.append(o.name)
        # Insert into mesh deque instance
        elif o.type == "EMPTY":
            pass
    if len(armatures) == 0 and len(meshes) == 0:
        print("No mesh or armature selected")
        return False
    OutputToFile(file_name, meshes, armatures, lhc)
    return True

def ExtractObjectsToFile(file_name, objects_to_export):
    if type(objects_to_export) == "dict":
        for name, time_lines in objects_to_export.items():
            print("--", name)
            if name in bpy.context.scene.objects.keys():
                pass
            else:
                print("{} {}".format("Unknown object", name))
                del objects_to_export[name]
        for name, time_lines in objects_to_export.items():
            pass
    else:
        raise(cUserException("Error expecting a dictionaray.", "ExtractObjectsToFile function."))

if __name__ == "__main__":
    print("------------------------------------------------------------------------")
    try:
        objects_to_export = dict()
        file_name = ""
        if os.name == "nt":
            file_name = os.path.expanduser("~") + "\\Documents\\Blender_Export.txt"
        else:
            raise(cUserException("Unknown operating system.  Do not have a path to save file.  Exiting.", "main"))
        major, minor, sub = bpy.app.version
        if major == 2 and minor == 79 and sub >= 0:
            if len(objects_to_export) == 0:
                if GatherSceneDataThenOutputToFile279(file_name):
                    print("Saved to", file_name)
                else:
                    ExtractObjectsToFile(file_name, objects_to_export)
        elif major == 2 and minor >= 80 and sub >= 0:
            if len(objects_to_export) == 0:
                if GatherSceneDataThenOutputToFile280(file_name):
                    print("Saved to", file_name)
                else:
                    ExtractObjectsToFile(file_name, objects_to_export)
        else:
            print("This script is not intended for Blender", bpy.app.version, "Exiting.")
    except cUserException as user:
        print(str(user))
    except OSError as os:
        print(os)
    except AttributeError as a:
        print(a)
    except KeyError as key:
        print(key)
    except ValueError as value:
        print(value)
    except:
        print("Unknown exception raised.")
