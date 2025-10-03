#!/usr/bin/env python3

import requests
import json
import time

# Test the streaming compilation and download functionality

# Get a working YAML template
print("🔍 Getting template preview...")
preview_response = requests.post("http://localhost:8000/api/v1/templates/preview", json={
    "template_id": 1,
    "assignments": [{"port_number": 1, "library_id": 1}],
    "include_comments": True
})

if preview_response.status_code != 200:
    print(f"❌ Failed to get template preview: {preview_response.status_code}")
    exit(1)

yaml_content = preview_response.json()["yaml"]
print(f"✅ Got template preview ({len(yaml_content)} characters)")

# Test streaming compilation
print("\n🚀 Starting streaming compilation...")
start_time = time.time()

response = requests.post(
    "http://localhost:8000/api/v1/templates/compile-stream",
    json={"yaml": yaml_content},
    stream=True
)

if response.status_code != 200:
    print(f"❌ Failed to start compilation: {response.status_code}")
    exit(1)

output_lines = []
binary_filename = None
compilation_success = False

print("📡 Streaming output:")
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            try:
                data = json.loads(line_str[6:])

                if data['type'] == 'output':
                    print(f"   {data['message']}")
                    output_lines.append(data['message'])
                elif data['type'] == 'complete':
                    compilation_success = data['success']
                    binary_filename = data.get('binary_filename')
                    print(f"\n🏁 Compilation finished: {'✅ SUCCESS' if compilation_success else '❌ FAILED'}")
                    if binary_filename:
                        print(f"📦 Binary file: {binary_filename}")
                elif data['type'] == 'error':
                    print(f"❌ Error: {data['message']}")
                elif data['type'] == 'status':
                    print(f"ℹ️  {data['message']}")

            except json.JSONDecodeError:
                print(f"⚠️  Invalid JSON: {line_str}")

compilation_time = time.time() - start_time
print(f"\n⏱️  Compilation took {compilation_time:.1f} seconds")

# Test binary download if compilation was successful
if compilation_success and binary_filename:
    print(f"\n📥 Testing binary download...")
    download_response = requests.get(f"http://localhost:8000/api/v1/templates/download/{binary_filename}")

    if download_response.status_code == 200:
        binary_size = len(download_response.content)
        print(f"✅ Successfully downloaded binary ({binary_size:,} bytes)")

        # Save to test file
        with open(f"/tmp/{binary_filename}", "wb") as f:
            f.write(download_response.content)
        print(f"💾 Saved binary to /tmp/{binary_filename}")
    else:
        print(f"❌ Failed to download binary: {download_response.status_code}")
else:
    print("⚠️  No binary file to download")

print("\n🎉 Streaming compilation and download test completed!")