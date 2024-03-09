#!/usr/bin/env python

import json
import os
import tempfile
import subprocess
from gltflib import GLTF

def glb_to_gltf_extract_resources(source_filepath):
    gltf = GLTF.load(source_filepath)
    glb_resource = gltf.get_glb_resource()
    resources_filepath = os.path.join(tempfile.gettempdir(), "gltf-resources.bin")
    gltf.convert_to_file_resource(glb_resource, resources_filepath)
    gltf_filepath = os.path.join(tempfile.gettempdir(), "gltf-file.gltf")
    gltf.export(gltf_filepath)

    return {
        "gltf_filepath" : gltf_filepath,
        "resources_filepath" : resources_filepath
    }

def extract_textures(source_gltf_filepath, resources_filepath):
    output_textures = []
    f = open(source_gltf_filepath)
    gltf_file = json.load(f)
    resource = open(resources_filepath, "rb")
    for image in gltf_file["images"]:
        buffer_view = gltf_file["bufferViews"][image["bufferView"]]
        start_byte = buffer_view["byteOffset"]
        byte_length = buffer_view["byteLength"]
        if image["mimeType"] == "image/png":
            image_file_name = f"gltf-temp-{image['name']}.png"
            image_file_path = os.path.join(tempfile.gettempdir(), image_file_name)
            output_image_file = open(image_file_path, "wb")
            resource.seek(start_byte)    
            output_image_file.write(resource.read(byte_length))    
            output_textures.append(image_file_name)
    return {
        "textures" : output_textures
    }

def compress_textures(textures):
    output_textures = {}
    for texture in textures:
        output_file_name = f"{texture}.jpeg"
        source_filepath = os.path.join(tempfile.gettempdir(), texture)
        output_filepath = os.path.join(tempfile.gettempdir(), output_file_name)
        print(source_filepath)
        print(output_filepath)
        subprocess.run(['magick', 'convert', source_filepath, '-quality', '75', '-resize', '256x256', output_filepath])
    return {
        "textures": output_textures
    }

def update_buffer_views(gltf_filepath, textures_paths):
    pass

def glft_to_glb(gltf_filepath, destination_filepath):
    output_glb = GLTF.load(gltf_filepath)
    output_glb.export(destination_filepath)    

def compress_glb(source_filepath, destination_filepath):
    print(source_filepath)
    print(destination_filepath)

    glb_extract_result = glb_to_gltf_extract_resources(source_filepath)
    extract_textures_result = extract_textures(glb_extract_result["gltf_filepath"], glb_extract_result["resources_filepath"])
    compress_textures_result = compress_textures(extract_textures_result["textures"])
    update_buffer_views(glb_extract_result["gltf_filepath"], compress_textures_result["textures"])
    glft_to_glb(glb_extract_result["gltf_filepath"], destination_filepath)

compress_glb("cat.glb", "compressed.glb")
