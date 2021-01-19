# Blender-script
X file exporter for blender.

It's a Blender 2.79b exporter to an x file format. Any other version of blender may not work.
It exports to a file named
"Blender_Export.txt"
to your documents folder.
The script will remove white spaces in the names of the armatures and meshes
and print them to the x file.
It exports armatures, meshes and animation with/without time markers. Just make sure
the objects have been selected.

By the way I'm not a Blender expert, nor am I an animation expert. So use at your
own discretion.

Must does:
1) Clean up code :) cause it looks messy.
2) Extracting data using left hand coordinate system isn't finished. Data is extracted
using right hand coordinate system.
