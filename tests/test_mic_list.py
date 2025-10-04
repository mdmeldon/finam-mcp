def test_mic_list():
    import json

    file = open("/Users/macbookpro3128/Downloads/response.json", "r")
    data = json.loads(file.read())

    mics = set()
    for row in data["assets"]:
        mics.add(row["mic"])

    print(mics)


if __name__ == "__main__":
    test_mic_list()