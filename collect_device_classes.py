import winreg
import pprint


def get_device_classes():
    """Windows Device Class 레지스트리에서 GUID와 Name을 가져오는 함수"""
    device_classes = []

    # HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class 경로 열기
    try:
        key_path = r"SYSTEM\CurrentControlSet\Control\Class"
        class_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)

        # 서브키(GUID) 개수 가져오기
        num_subkeys = winreg.QueryInfoKey(class_key)[0]

        # 각 GUID 검색
        for i in range(num_subkeys):
            guid = winreg.EnumKey(class_key, i)

            try:
                # GUID 서브키 열기
                guid_key = winreg.OpenKey(class_key, guid)

                try:
                    # 'Class' 값 가져오기 (디바이스 클래스 이름)
                    class_name = winreg.QueryValueEx(guid_key, "Class")[0]
                except FileNotFoundError:
                    class_name = ""

                try:
                    # 'UpperFilters' 값 가져오기
                    upper_filters = winreg.QueryValueEx(guid_key, "UpperFilters")[0]
                except FileNotFoundError:
                    upper_filters = ""

                try:
                    # 'LowerFilters' 값 가져오기
                    lower_filters = winreg.QueryValueEx(guid_key, "LowerFilters")[0]
                except FileNotFoundError:
                    lower_filters = ""

                device_classes.append(
                    {
                        "GUID": guid[1:-1],
                        "Name": class_name,
                        "UpperFilters": upper_filters,
                        "LowerFilters": lower_filters,
                    }
                )

                winreg.CloseKey(guid_key)
            except WindowsError:
                pass

        winreg.CloseKey(class_key)
    except WindowsError as e:
        print(f"오류 발생: {e}")

    return device_classes


if __name__ == "__main__":
    # 디바이스 클래스 정보 가져오기
    device_classes = get_device_classes()

    # 결과 출력
    print(f"총 {len(device_classes)}개의 디바이스 클래스 발견:")
    pprint.pprint(device_classes)

    # CSV 파일로 저장 (선택사항)
    import csv

    with open("device_classes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["GUID", "Name", "UpperFilters", "LowerFilters"]
        )
        writer.writeheader()
        writer.writerows(device_classes)
    print("device_classes.csv 파일로 저장됨")
