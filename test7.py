#!/usr/bin/env python

import copy
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

        buffer_view = gltf_file["bufferViews"][image_buffer_index]
        image_byte_offset = int(buffer_view["byteOffset"])

        image_filepath = os.path.join(tempfile.gettempdir(), f"gltf-temp-{image_name}.png.jpeg")

        with open(image_filepath, 'rb') as image_file:
            compressed_image_data = bytearray(image_file.read())

        compressed_image_data_length = len(compressed_image_data)

        padding_byte = 0x20
        need_padding_bytes_length = 4 - compressed_image_data_length % 4
        print(f"need_padding_bytes_length: {need_padding_bytes_length}")
        for i in range(need_padding_bytes_length):
            compressed_image_data.append(0x20)

        compressed_image_data_length = len(compressed_image_data)
        end_byte = image_byte_offset + compressed_image_data_length
        resources_data[image_byte_offset : end_byte] = compressed_image_data

        original_buffer_byte_start = buffer_view["byteOffset"]
        original_buffer_length = buffer_view["byteLength"] - buffer_view["byteLength"] % 4

        image["mimeType"] = "image/jpeg"
        #buffer_view["byteLength"] = compressed_image_data_length

        print(f"original_buffer_byte_start: {original_buffer_byte_start}")
        print(f"original_buffer_length: {original_buffer_length}")

        bytes_difference = original_buffer_length - compressed_image_data_length
        if bytes_difference % 4 != 0:
            print("argh!!!!")
            exit(1)

        unused_byte_start = end_byte - 1
        unused_byte_end = unused_byte_start + bytes_difference
        #unused_byte_end = unused_byte_start + 4

        print(f'{resources_data[unused_byte_start]:0x}')
        print(f'{resources_data[unused_byte_end]:0x}')

        del resources_data[unused_byte_start : unused_byte_end]

        print(f"bytes_difference: {format_size(bytes_difference)}")

        for updating_buffer in gltf_file["bufferViews"]:
            if updating_buffer["byteOffset"] == buffer_view["byteOffset"]:
                updating_buffer["byteLength"] = compressed_image_data_length
                print("pass changed bufferView")
                pass
            elif updating_buffer["byteOffset"] > unused_byte_end:
                updating_buffer["byteOffset"] = updating_buffer["byteOffset"] - bytes_difference
                if updating_buffer["byteOffset"] % 4 != 0:
                    print(f"{updating_buffer['byteOffset']}")
                    print(f"{updating_buffer['byteOffset'] % 4}")
            else:
                print(f"pass bufferView - {updating_buffer['byteOffset']}")

        print(f"image: {image_name} - {format_size(compressed_image_data_length)} replacement_data_length % 4 = {compressed_image_data_length % 4}")

    gltf_file["buffers"][0]["uri"] = "gltf-resources.bin.output.bin"
    gltf_file["buffers"][0]["byteLength"] = os.path.getsize("/tmp/gltf-resources.bin.output.bin")

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

process_glb("input.glb", "output.glb")