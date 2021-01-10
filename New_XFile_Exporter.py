import bpy, mathutils, math, copy
from collections import deque
from os import path

# does not use cMesh to extract to x file
# reads data from blender file to extract to x file

def RemoveWhiteSpace(s):
    if type(s).__name__ == 'str':
        tmp = ''
        for i in range(len(s)):
            if s[i] == ' ':
                tmp += '_'
            else:
                tmp += s[i]
        return tmp

def _Indentformat(hfile, indent, s, a):
    arg = 0
    for i in range(0, len(s)):
        if s[i] == '{':
            if (i + 1) != len(s):
                if s[i + 1] == '}':
                    arg += 1
    if arg != len(a):
        print('arguments differ')
        return False
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

def _Indent(hfile, indent, title = None):
    s = ''
    for i in range(0, indent):
        s += '  '
    if title != None:
        s += title
    hfile.write(s)
"""
def VectorToFile(hfile, indent, v):
    format_string = "{}; {}; {};"
    s = str(v[0]) + str(v[1]) + str(v[2])
    _Indent(hfile, indent, s)
    del format_string, s
"""

def _ExtractMatrixToFile(hfile, indent, matrix, lhc = False, title = None):
    m = matrix.copy()
    if title == None:
        title = "Matrix4x4 {"
    _Indent(hfile, indent, title)
    s = ''
    for row in m.transposed():
        s += " {}, {}, {}, {},".format(row[0], row[1], row[2], row[3])
    for r in range(0, len(s) - 1):
        hfile.write(s[r])
    if title == "Matrix4x4 {":
        s = '; }\n'
    else:
        s = ';; }\n'
    hfile.write(s)

def _GetLeftHandCoordinateMatrix(matrix):
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

def _ExtractMatrices(hfile, indent, matrix, lhc):
    for m in matrix:
        if lhc == False:
            _ExtractMatrixToFile(hfile, indent, m)
        else:
            mat = _GetLeftHandCoordinateMatrix(m)
            _ExtractMatrixToFile(hfile, indent, mat)

def _ExtractTextureCoordinateToFile(hfile, indent, obj):
    if len(obj.data.uv_layers) == 0:
        return
    format_string = "-{}\n--{}\n"
    uv_layer = obj.data.uv_layers[obj.data.uv_layers.active_index]
    args = ["MeshTextureCoords {", str(len(uv_layer.data)) + ";"]
    _Indentformat(hfile, indent, format_string, args)
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
    _Indentformat(hfile, indent, format_string, args)
    _Indent(hfile, indent, "} // End of MeshTextureCoords\n")
    del format_string, args, sep1
    
def _ExtractNormalToFile(hfile, indent, obj, lhc):
    normals = []
    normal_indices = []
    sep1 = deque()
    format_string = "-{}\n+-{}\n"
    args = ["MeshNormals {", str(len(obj.data.polygons)) + ";"]
    _Indentformat(hfile, indent, format_string, args)
    for i in range(len(obj.data.polygons) - 1):
        sep1.append(',')
    sep1.append(';')
    format_string = ""
    args = []
    if lhc:
        for p in obj.data.polygons:
            tmp = []
            normals.append(mathutils.Vector((p.normal.x, p.normal.y, p.normal.z * -1)))
            format_string += "-{}{}{}\n"
            args += [str(p.normal.x) + '; ', str(p.normal.y) + '; ', str(p.normal.z * -1) + ';' + sep1.popleft()]
            for l in range(p.loop_start, p.loop_total + p.loop_start):
                tmp.append(len(normals) - 1)
            normal_indices.append(tmp)
    else:
        for p in obj.data.polygons:
            tmp = []
            normals.append(p.normal)
            format_string += "-{}{}{}\n"
            args += [str(p.normal.x) + '; ', str(p.normal.y) + '; ', str(p.normal.z) + ';' + sep1.popleft()]
            for l in range(p.loop_start, p.loop_total + p.loop_start):
                tmp.append(len(normals) - 1)
            normal_indices.append(tmp)
    indent += 1
    _Indentformat(hfile, indent, format_string, args)
    format_string = ''
    args.clear()
    for i in range(len(normal_indices) - 1):
        sep1.append(',')
    sep1.append(';')
    sep2 = deque()
    _Indent(hfile, indent, str(len(normal_indices)) + ';\n')
    max_index = len(normal_indices)
    for l in normal_indices:
        format_string += "-{}"
        args += [str(len(l)) + ';']
        for i in range(len(l) - 1):
            sep2.append(',')
        sep2.append(';')
        for i in range(len(l)):
            format_string += " {}"
            args += [str(l[i]) + sep2.popleft()]
        args[len(args) - 1] += sep1.popleft() + '\n'
    _Indentformat(hfile, indent, format_string, args)
    indent -= 1
    s = "} // End of MeshNormals" + obj.name + " \n"
    _Indent(hfile, indent, s)
    del normal_indices, normals, l, s

def _ExtractMaterials(hfile, indent, obj):
    s = "MeshMaterialList {\n"
    _Indent(hfile, indent, s)
    indent += 1
    s = "{}{}\n".format(len(obj.data.materials), ';')
    _Indent(hfile, indent, s)
    s = "{}{}\n".format(len(obj.data.polygons), ';')
    _Indent(hfile, indent, s)
    for i, p in enumerate(obj.data.polygons):
        if i != (len(obj.data.polygons) - 1):
            s = "{}{}\n".format(p.material_index, ',')
            _Indent(hfile, indent, s)
        else:
            s = str(obj.data.polygons[len(obj.data.polygons) - 1].material_index) + ';\n'
            _Indent(hfile, indent, s)
    for m in obj.data.materials:
        s = "Material " + RemoveWhiteSpace(m.name) + " {\n"
        _Indent(hfile, indent, s)
        indent += 1
        c = m.diffuse_color
        s = "{}; {}; {}; {};;\n".format(str(c[0]), str(c[1]), str(c[2]), m.alpha)
        _Indent(hfile, indent, s)
        c = m.specular_hardness
        s = "{}{}".format(str(c), ';\n')
        _Indent(hfile, indent, s)
        c = m.specular_color
        s = "{}; {}; {};;\n".format(str(c[0]), str(c[1]), str(c[2]))
        _Indent(hfile, indent, s)
        s = "0.0; 0.0; 0.0;;\n"
        _Indent(hfile, indent, s)    
        if m.active_texture != None:
            if m.active_texture.type == "IMAGE":
                s = "TextureFilename {\n"
                _Indent(hfile, indent, s)
                p, f = path.split(m.active_texture.image.filepath)
                if len(f) > 0:
                    s = "{}{}{}\n".format("\"", f, "\";")
                else:
                    s = "{}{}{}\n".format("\"", m.active_texture.image.filepath, "\";")
                _Indent(hfile, indent + 1, s)
                s = "{}\n".format('} // End of TextureFileName')
                _Indent(hfile, indent, s)
        indent -= 1
        s = "{} {}\n".format("} // End of Material", RemoveWhiteSpace(m.name))
        _Indent(hfile, indent, s)
    indent -= 1
    s = "} // End of MeshMaterialList\n"
    _Indent(hfile, indent, s)
    
def _GetMatrixOffset(hfile, indent, mesh, bone_name):
    mesh_l, mesh_r, mesh_s = mesh.matrix_world.decompose()
    parent = bpy.context.scene.objects[mesh.parent.name]
    if bone_name not in parent.data.bones:
        return False
    bone_l, bone_r, bone_s = parent.data.bones[bone_name].matrix_local.decompose()
    parent_l, parent_r, parent_s = parent.matrix_world.decompose()
    l, r, s = (parent.matrix_world * parent.data.bones[bone_name].matrix_local).decompose()
    m = mathutils.Matrix.Translation(mesh_l - l)
    sep = deque()
    for i in range(15):
        sep.append(', ')
    sep.append(';')
    format_string = "--"
    args = []
    while len(sep) > 0:
        format_string += "{}" + sep.popleft()
    format_string += ";\n"
    for row in m:
        for col in row:
            args.append(str(col))
    _Indentformat(hfile, indent, format_string, args)
    del format_string, args, mesh_l, mesh_r, mesh_s
    del parent, bone_l, bone_r, bone_s
    del parent_l, parent_r, parent_s
    del l, r, s, m, sep
    return True
    
def _ExtractWeights(hfile, indent, obj):
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
        _Indentformat(hfile, indent, format_string, args)
        indices = []
        weight = []
        format_string = "--{};\n"
        for i in range(len(weights[group]) - 1):
            sep.append(',')
        sep.append(';')
        master = sep.copy()
        args = [str(len(weights[group]))]
        _Indentformat(hfile, indent, format_string, args)
        for i, w in weights[group]:
            indices.append(i)
            weight.append(w)
        format_string = ""
        args = []
        for i in indices:
            format_string += "--{}{}\n"
            args += [str(i), sep.popleft()]
        _Indentformat(hfile, indent, format_string, args)
        format_string = ""
        args = []
        sep = master.copy()
        for w in weight:
            format_string += "--{}{}\n"
            args += [str(w), sep.popleft()]
        _Indentformat(hfile, indent, format_string, args)
        _GetMatrixOffset(hfile, indent, obj, obj.vertex_groups[group].name)
        format_string = "-{} {}\n"
        args = ["}", "// End of SkinWeights"]
        _Indentformat(hfile, indent, format_string, args)
        sep.clear()
        master.clear()
    del sep, master, weights, args, format_string

def _ExtractVerticesToFile(hfile, indent, obj, lhc):
    if type(obj).__name__ != "Object":
        return False
    v = obj.data.vertices
    sep = deque()
    for i in range(len(v) - 1):
        sep.append(',')
    sep.append(';')
    format_string = ''
    args = []
    if lhc:
        for i in range(0, len(v)):
            format_string += '-{}; {}; {};' + sep.popleft() + '\n'
            args.extend([str(v[i].co.x), str(v[i].co.y), str(v[i].co.z * -1)])
        _Indentformat(hfile, indent, format_string, args)
    else:
        for i in range(0, len(v)):
            format_string += '-{}; {}; {};' + sep.popleft() + '\n'
            args.extend([str(v[i].co.x), str(v[i].co.y), str(v[i].co.z)])
        _Indentformat(hfile, indent, format_string, args)
    del format_string, args, sep, v
    
def _ExtractMeshPolygons(hfile, indent, obj, lhc):
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
        if lhc == False:
            normal_args.extend([str(polygon.normal.x), str(polygon.normal.y), str(polygon.normal.z)])
        else:
            normal_args.extend([str(polygon.normal.x), str(polygon.normal.y), str(polygon.normal.z * -1)])
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
    _Indentformat(hfile, indent, format_string, args)
    face_string += '-{} {}\n'
    face_args.extend(['}', '// End of MeshNormals'])
    _Indentformat(hfile, indent, normal_string, normal_args)
    _Indentformat(hfile, indent, face_string, face_args)
    del normal_string, normal_args
    del format_string, args
    del sep, sep2, normal_sep
    del face_string, face_args
    
def _ExtractMeshInfoToFile(hfile, obj, matrix, lhc = False):
    if type(hfile).__name__ != "TextIOWrapper":
        return False
    if type(obj).__name__ != "Object":
        return False
    if type(matrix).__name__ != "list":
        return False
    indent = 0
    format_string = "-{} {} {}\n+-{}{}\n"
    args = ["Mesh", RemoveWhiteSpace(obj.name), "{", str(len(obj.data.vertices)), ";"]
    _Indentformat(hfile, indent, format_string, args)
    indent += 1
    _ExtractVerticesToFile(hfile, indent, obj, lhc)
    del format_string
    args.clear()
    _ExtractMeshPolygons(hfile, indent, obj, lhc)
    if len(obj.data.uv_textures) > 0:
        for index, layer in enumerate(obj.data.uv_textures):
            if layer.active == True:
                uv_layer_active_index = index
                _ExtractTextureCoordinateToFile(hfile, indent, obj)
                break
        del index, layer, uv_layer_active_index
    if len(obj.material_slots) > 0:
        _ExtractMaterials(hfile, indent, obj)
    if len(obj.vertex_groups) > 0 and obj.parent != None:
        if obj.parent.select:
            _ExtractWeights(hfile, indent, obj)
    _ExtractMatrices(hfile, indent, matrix, lhc)
    format_string = "} // End of mesh " + RemoveWhiteSpace(obj.name) + "\n\n"
    hfile.write(format_string)
    del format_string
    return True
    
def _ExtractArmaturesInfoToFile(hfile, armatures, lhc = False):
    if type(hfile).__name__ != "TextIOWrapper":
        return False
    if type(armatures).__name__ != "deque":
        return False
    if len(armatures) <= 0:
        return True
    bone_stack = list()
    indent = 0
    for currarmature in reversed(armatures):
        _Indent(hfile, indent, "\nFrame " + RemoveWhiteSpace(currarmature) + " {\n")
        a = bpy.context.scene.objects[currarmature]
        if a.children != None:
            for child in a.children:
                _Indent(hfile, indent, '{' + child.name + '}\n')
        if lhc:
            if a.parent != None:
                matrix = _GetLeftHandCoordinateMatrix(a.matrix_local.copy())
            else:
                matrix = a.matrix_world.copy()
        else:
            if a.parent != None:
                matrix = a.matrix_local.copy()
            else:
                matrix = a.matrix_world.copy()
        _ExtractMatrixToFile(hfile, indent + 1, matrix, lhc, "FrameTransformMatrix {")
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
                _Indent(hfile, indent, s)
                continue
            _Indent(hfile, indent, 'Frame ' + currbone + ' {\n')
            s = "Vector { " + str(0) + "; " + str(a.data.bones[currbone].length) + "; " + str(0) + ";; }\n"
            _Indent(hfile, indent + 1, s)
            if lhc:
                matrix = _GetLeftHandCoordinateMatrix(a.data.bones[currbone].matrix_local.copy())
                _ExtractMatrixToFile(hfile, indent + 1, matrix, lhc, "FrameTransformMatrix {")
            else:
                _ExtractMatrixToFile(hfile, indent + 1, a.data.bones[currbone].matrix_local.copy(), lhc, "FrameTransformMatrix {")
            if len(a.data.bones[currbone].children) > 0:
                bone_stack.append((indent, '} // End of ' + currbone + '\n'))
                for child in a.data.bones[currbone].children:
                    bone_stack.append((indent + 1, child.name, child.parent.name))
                continue
            _Indent(hfile, indent, '} // End of ' + currbone + '\n')
        indent -= 1
        _Indent(hfile, indent, '} // End of ' + currarmature + '\n')
    hfile.write("\n")

def _Rotate(obj):
    if obj.rotation_mode == 'QUATERNION':
        e = obj.rotation_quaternion
        return ("{}; {}, {}, {}, {};", [str(len(e)), str(e.w), str(e.x), str(e.y), str(e.z)])
    else:
        e = obj.rotation_euler.copy()
        return ("{}; {}, {}, {};", [str(len(e)), str(e.x), str(e.y), str(e.z)])

def _Scale(obj):
    return ("{}; {}, {}, {};", [str(len(obj.scale)), str(obj.scale[0]), str(obj.scale[1]), str(obj.scale[2])])

def _Translate(obj):
    return ("{}; {}, {}, {};", [str(len(obj.location)), str(obj.location[0]), str(obj.location[1]), str(obj.location[2])])

def _ExtractAnimationDataPerFrames(hfile, indent, time, type, sep, name):
    format_string = "-{} {}\n+-{};\n-{};\n"
    args = ["AnimationKey", "{", str(type[0]), str(time[1] - time[0])]
    _Indentformat(hfile, indent, format_string, args)
    obj = bpy.context.scene.objects[name]
    indent += 1
    format_string = ""
    args.clear()
    for frame in range(time[0], time[1]):
        bpy.context.scene.frame_set(frame)
        args.append(str(frame))
        r = type[1](obj) #function call
        format_string += '-{}; ' + r[0] + ';' + sep.popleft() + '\n'
        args.extend(r[1])
    _Indentformat(hfile, indent, format_string, args)
    indent -= 1
    format_string = "-{} {}\n"
    args.clear()
    args = ["}", "// End of AnimationKey"]
    _Indentformat(hfile, indent, format_string, args)

def _ExtractMarkers(timelines):
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
        
def _GetMeshAnimation(hfile, indent, time_slot, obj):
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
    _Indentformat(hfile, indent, format_string, args)
    sep2 = copy.copy(sep1)
    _ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (1, _Scale), sep2, obj.name)
    sep2 = copy.copy(sep1)
    _ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (2, _Translate), sep2, obj.name)
    sep2 = copy.copy(sep1)
    print("Exporting rotation")
    _ExtractAnimationDataPerFrames(hfile, indent + 1, (time_slot[0][0], time_slot[1][0]), (0, _Rotate), sep2, obj.name)
    del format_string
    format_string = '-{}\n'
    args.clear()
    args.extend(["} // End of Animation"])
    _Indentformat(hfile, indent, format_string, args)
    del sep1, sep2, format_string, args, total

def GetArmatureAnimation(hfile, indent, time_slot, obj):
    sep = deque()
    sep1 = deque()
    for bone in obj.pose.bones:
        print(bone.name)
        format_string = '-{} {} {}\n--{}{}{}\n'
        args = ["Animation", time_slot[0][1], '{', '{', bone.name, '}']
        _Indentformat(hfile, indent, format_string, args)
        indent += 1
        format_string = "-{}\n--{}; {}\n"
        args = ["AnimationKey {", str(0), "// Rotation"]
        _Indentformat(hfile, indent, format_string, args)
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
            bpy.context.scene.frame_set(frame)
            if bone.rotation_mode == "QUATERNION":
                #r = bone.rotation_quaternion
                l, r, s = bone.matrix.decompose()
                format_string += "--{}; {}; {}, {}, {}, {};;{}\n"
                args += [str(frame), str(len(r)), str(r.w), str(r.x), str(r.y), str(r.z), sep.popleft()]
            else:
                r = bone.rotation_euler
                format_string += "--{}; {}; {}, {}, {};;{}\n"
                args += [str(frame), str(len(r)), str(r.x), str(r.y), str(r.z), sep.popleft()]
            count += 1
        _Indentformat(hfile, indent, "--{};\n", [str(count)])
        _Indentformat(hfile, indent, format_string, args)
        format_string = '-{} {}\n'
        args.clear()
        args = ['}', "// End of AnimationKey"]
        _Indentformat(hfile, indent, format_string, args)
        format_string = '-{}\n--{}; {}\n'
        args = ["AnimationKey {", str(2), "// Location"]
        _Indentformat(hfile, indent, format_string, args)
        count = 0
        format_string = ""
        args.clear()
        for frame in range(time_slot[0][0], time_slot[1][0] + 1):
            bpy.context.scene.frame_set(frame)
            #l = bone.location
            l, r, s = bone.matrix.decompose()
            format_string += "--{}; {}; {}, {}, {};;{}\n"
            args += [str(frame), str(len(l)), str(l.x), str(l.y), str(l.z), sep1.popleft()]
            count += 1
        _Indentformat(hfile, indent, "--{};\n", [str(count)])
        _Indentformat(hfile, indent, format_string, args)
        format_string = "-{}\n"
        args = ["} // End of AnimationKey"]
        _Indentformat(hfile, indent, format_string, args)
        indent -= 1
        format_string = "-{} {} {}\n"
        args = ['}', "// End of Animation", time_slot[0][1]]
        _Indentformat(hfile, indent, format_string, args)
    del format_string, args
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    
def _Markers(hfile, indent, markers, animate_data):
    if len(animate_data["MESH"]) > 0:
        for mesh_name in animate_data["MESH"]:
            format_string = "{} {} {}\n"
            args = ["AnimationSet", mesh_name, '{']
            _Indentformat(hfile, indent, format_string, args)
            for index, marker in enumerate(markers):
                if index != (len(markers) - 1):
                    _GetMeshAnimation(hfile, indent, (marker, markers[index + 1]), bpy.context.scene.objects[mesh_name])
            del format_string
            format_string = "{} {} {}\n\n"
            args.clear()
            args = ['}', "// End of AnimationSet", mesh_name]
            _Indentformat(hfile, indent, format_string, args)
    if len(animate_data["ARMATURE"]) > 0:
        for armature_name in animate_data["ARMATURE"]:
            format_string = "{} {} {}\n"
            args = ["AnimationSet", armature_name, '{']
            _Indentformat(hfile, indent, format_string, args)
            for index, marker in enumerate(markers):
                if index != (len(markers) - 1):
                    GetArmatureAnimation(hfile, indent, (marker, markers[index + 1]), bpy.context.scene.objects[armature_name])
            del format_string
            format_string = "{} {} {}\n\n"
            args.clear()
            args = ['}', "// End of AnimationSet", armature_name]
            _Indentformat(hfile, indent, format_string, args)
    del args, format_string

def _ExtractAnimation(hfile, indent, armatures, mesh, lhc):
    markers = list()
    _ExtractMarkers(markers)
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
    _Indentformat(hfile, indent, format_string, args)
    format_string = ''
    args.clear()
    _Markers(hfile, indent, markers, animate_data)
    
def _OutputToFile(filename, mesh, armatures, lhc):
    p = path.expanduser("~") + "\\documents\\"
    if filename == None:
        filename = "Armature_Animation1.txt"
    indent = 0
    with open(p + filename, "w") as hfile:
        s = "xof 0303txt 0032\n"
        if lhc:
            s += "// Left hand coordinate system\n"
        else:
            s += "// Right hand coordinate system\n"
        if (len(mesh)) > 0:
            s += "// Face of polygons are counter clockwise\n"
            s += "{} {}\n".format("// Number of meshes", len(mesh))
        if (len(armatures)) > 0:
            s += "{} {}\n".format("// Number of armatures ", len(armatures))
        for key in mesh.keys():
            s += "// Mesh " + key + '\n'
        s += '\n'
        hfile.write(s)
        del s, p, filename
        for name in list(mesh):
            if _ExtractMeshInfoToFile(hfile, bpy.context.scene.objects[name], mesh[name], lhc) == False:
                print("Could not extract", name)
            else:
                print(name, "extracted")
        if len(armatures) > 0:
            _ExtractArmaturesInfoToFile(hfile, armatures, lhc)
        _ExtractAnimation(hfile, indent + 1, armatures, mesh, lhc)

def GatherSceneDataThenOutputToFile(filename = None, lhc = False):
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
    _OutputToFile(filename, mesh, armatures, lhc)
    return True

if __name__ == "__main__":
    print("----------------------------------------------------------------")
    major, minor, sub = bpy.app.version
    if major != 2 or minor < 70:
        print("This script may not be compatible with this Blender version.")
    file_name = "Blender_Export.txt"
    if GatherSceneDataThenOutputToFile(file_name):
        print("Saved to", path.expanduser("~") + "\\Documents\\" + file_name)
