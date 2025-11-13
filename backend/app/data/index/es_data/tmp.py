import json

def load_unique_objects(json_path):
    """
    Read JSON in format {"id": ["obj1", "obj2"]} 
    and return a sorted list of all unique objects.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_objects = set()

    for obj_list in data.values():
        if isinstance(obj_list, list):
            for obj in obj_list:
                if isinstance(obj, str) and obj.strip():
                    all_objects.add(obj.strip())

    return sorted(all_objects)


# Example usage
if __name__ == "__main__":
    path = "OBJECT.json"  # đổi path của bạn
    unique_objects = load_unique_objects(path)

    print("Total objects:", len(unique_objects))
    print(unique_objects)
