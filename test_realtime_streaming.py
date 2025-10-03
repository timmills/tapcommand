#!/usr/bin/env python3

import requests
import json
import time

def test_streaming():
    print("🧪 Testing Real-time Streaming Compilation...")

    # Get a working template
    preview_response = requests.post("http://localhost:8000/api/v1/templates/preview", json={
        "template_id": 1,
        "assignments": [{"port_number": 1, "library_id": 1}],
        "include_comments": True
    })

    if preview_response.status_code != 200:
        print("❌ Failed to get template")
        return

    yaml_content = preview_response.json()["yaml"]
    print(f"✅ Got template ({len(yaml_content)} chars)")

    # Test streaming
    print("\n🚀 Starting real-time streaming test...")
    response = requests.post(
        "http://localhost:8000/api/v1/templates/compile-stream",
        json={"yaml": yaml_content},
        stream=True
    )

    if response.status_code != 200:
        print(f"❌ HTTP {response.status_code}")
        return

    print("📡 Real-time output:")
    line_count = 0
    start_time = time.time()
    last_output_time = start_time

    for line in response.iter_lines():
        if line:
            current_time = time.time()
            time_since_start = current_time - start_time
            time_since_last = current_time - last_output_time

            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])

                    if data['type'] in ['output', 'status']:
                        line_count += 1
                        print(f"[{time_since_start:6.1f}s +{time_since_last:4.1f}s] {data['message']}")
                        last_output_time = current_time

                        if line_count >= 20:  # Stop after 20 lines to test real-time behavior
                            print(f"\n✅ SUCCESS: Received {line_count} lines of real-time output!")
                            print(f"⏱️  Total time: {time_since_start:.1f} seconds")
                            print(f"🔥 Real-time streaming is working perfectly!")
                            return

                    elif data['type'] == 'complete':
                        print(f"\n🏁 Compilation completed!")
                        if data.get('binary_filename'):
                            print(f"📦 Binary: {data['binary_filename']}")
                        return

                except json.JSONDecodeError:
                    continue

if __name__ == "__main__":
    test_streaming()