#!/usr/bin/env python

import os
import json
import tempfile
from gltflib import GLTF
import subprocess

def png_to_jpg(source_file, output_file):
    print(source_file)
    print(output_file)
    subprocess.run(['magick', 'convert', source_file, '-quality', '75', output_file])

def glb_to_gltf(source_path, output_path, resources_filepath):
    gltf = GLTF.load(source_path)
    glb_resource = gltf.get_glb_resource()
    gltf.convert_to_file_resource(glb_resource, resources_filepath)
    gltf.export(output_path)

def extract_textures(gltf_path, temporary_gltf_file, resources_filepath):
    temporary_directory = tempfile.gettempdir()
    print(gltf_path)
    f = open(gltf_path)
    gltf_file = json.load(f)
    resource = open(resources_filepath, "rb")
    for image in gltf_file["images"]:
        bufferView = gltf_file["bufferViews"][image["bufferView"]]
        start_byte = bufferView["byteOffset"]
        bytes_length = bufferView["byteLength"]
        if image["mimeType"] == "image/png":
            image_file_name = f"gltf-temp-{image['name']}.png"
            image_file_path = os.path.join(temporary_directory, image_file_name)
            output_image_file = open(image_file_path, "wb")
            resource.seek(start_byte)    
            output_image_file.write(resource.read(bytes_length))
            png_to_jpg(image_file_path, f"{image_file_path}.jpg")

def compress_glb(source_path, output_path):
    temporary_directory = tempfile.gettempdir()
    print(f"temporary_directory: {temporary_directory}")
    temporary_gltf_file = os.path.join(temporary_directory, "gltf-temp.gltf")
    temporaty_resources_filepath = f"{temporary_gltf_file}.bin"
    print(f"f{temporaty_resources_filepath}")
    glb_to_gltf(source_path, temporary_gltf_file, temporaty_resources_filepath)
    extract_textures(temporary_gltf_file, temporary_gltf_file, temporaty_resources_filepath)

compress_glb("cat.glb", "compressed.gltf")