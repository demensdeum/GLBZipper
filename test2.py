#!/usr/bin/env python

import json
import os
import tempfile
import subprocess
import shutil
from gltflib import GLTF

def format_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_in_bytes)
    for unit in units[:-1]:
        if size < 1024.0:
            break
        size /= 1024.0

    return f"{size:.2f} {unit}"

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
            image_filename = f"gltf-temp-{image['name']}.png"
            image_filepath = os.path.join(tempfile.gettempdir(), image_filename)
            output_image_file = open(image_filepath, "wb")
            resource.seek(start_byte)    
            output_image_file.write(resource.read(byte_length))    
            output_textures.append(image_filename)
    return {
        "textures" : output_textures
    }

def compress_textures(textures):
    output_textures = {}
    for texture in textures:
        output_filename = f"{texture}.jpeg"
        source_filepath = os.path.join(tempfile.gettempdir(), texture)
        output_filepath = os.path.join(tempfile.gettempdir(), output_filename)
        print(source_filepath)
        print(output_filepath)
        subprocess.run(['magick', 'convert', source_filepath, '-quality', '75', '-resize', '256x256', output_filepath])
    return {
        "textures": output_textures
    }

def glft_to_glb(gltf_filepath, destination_filepath):
    output_glb = GLTF.load(gltf_filepath)
    output_glb.export(destination_filepath)    

def update_resources(gltf_filepath, source_resources_filepath, textures, destination_resources_filepath, output_gltf_filepath):
    print(gltf_filepath)
    print(source_resources_filepath)
    print(destination_resources_filepath)

    f = open(gltf_filepath)
    gltf_file = json.load(f)

    with open(source_resources_filepath, 'rb') as source_resources_file:
        resources_data = bytearray(source_resources_file.read())

    for index, image in enumerate(gltf_file["images"]):
        image_name = image["name"]
        image_buffer_index = image["bufferView"]

        bufferView = gltf_file["bufferViews"][image_buffer_index]
        image_byte_offset = int(bufferView["byteOffset"])

        image_filepath = os.path.join(tempfile.gettempdir(), f"gltf-temp-{image_name}.png.jpeg")

        with open(image_filepath, 'rb') as image_file:
            image_data = bytearray(image_file.read())

        image_data_length = len(image_data)

        padding_byte = 0x20
        need_padding_bytes_length = 4 - image_data_length % 4
        print(f"need_padding_bytes_length: {need_padding_bytes_length}")
        for i in range(need_padding_bytes_length):
            image_data.append(0x20)

        image_data_length = len(image_data)

        # print(resources_data)
        # print(image_byte_offset)
        resources_data[image_byte_offset:image_byte_offset + image_data_length] = image_data

        print(f"image: {image_name} - {format_size(image_data_length)} replacement_data_length % 4 = {image_data_length % 4}")

        bufferView["byteLength"] = image_data_length
        image["mimeType"] = "image/jpeg"

    gltf_file["buffers"][0]["uri"] = "gltf-resources.bin.output.bin"

    with open(output_gltf_filepath, 'w') as output_gltf_file:
        json.dump(gltf_file, output_gltf_file)

    with open(destination_resources_filepath, 'wb') as destination_resources_file:
        destination_resources_file.write(resources_data)
    

def process_glb(source_filepath, destination_filepath = "", only_extract_textures = False):
    print(source_filepath)
    print(destination_filepath)

    glb_extract_result = glb_to_gltf_extract_resources(source_filepath)
    gltf_filepath = glb_extract_result["gltf_filepath"]
    extract_textures_result = extract_textures(gltf_filepath, glb_extract_result["resources_filepath"])
    if only_extract_textures:
        exit(0)
    textures = extract_textures_result["textures"]
    compress_textures_result = compress_textures(textures)
    resources_filepath = glb_extract_result["resources_filepath"]
    output_gltf_filepath = f"{glb_extract_result['gltf_filepath']}.output.gltf"
    output_resources_filepath = f"{resources_filepath}.output.bin"
    update_resources(glb_extract_result["gltf_filepath"], resources_filepath, textures, output_resources_filepath, output_gltf_filepath)
    glft_to_glb(output_gltf_filepath, destination_filepath)

process_glb("cat.glb", "compressed.glb")
#process_glb("compressed.glb", only_extract_textures=True)
