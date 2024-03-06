import os
import tempfile
from gltflib import GLTF

def compress_glb(source_path, output_path):
    temporary_directory = tempfile.gettempdir()
    print(f"temporary_directory: {temporary_directory}")
    gltf = GLTF.load(source_file)
    glb_resource = gltf.get_glb_resource()
    gltf.convert_to_file_resource(glb_resource, 'resource.bin')
    gltf.export(output_path)    

if __name__ == "__main__":
    compress_glb()