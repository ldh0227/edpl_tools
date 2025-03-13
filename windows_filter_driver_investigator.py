import os
import csv
import re
import socket
import subprocess
import winreg
import ctypes
from ctypes import windll, wintypes
import pefile

from loguru import logger

log_filename = "filter_driver_status.log"
logger.add(log_filename)


def get_device_classes_with_filters():
    """디바이스 클래스에서 Upperfilters와 Lowerfilters 정보 가져오기"""
    filter_info = []

    try:
        key_path = r"SYSTEM\CurrentControlSet\Control\Class"
        class_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)

        num_subkeys = winreg.QueryInfoKey(class_key)[0]

        for i in range(num_subkeys):
            guid = winreg.EnumKey(class_key, i)

            try:
                guid_key = winreg.OpenKey(class_key, guid)

                try:
                    class_name = winreg.QueryValueEx(guid_key, "Class")[0]
                except (FileNotFoundError, WindowsError):
                    class_name = ""

                device_class = {
                    "GUID": guid,
                    "Name": class_name,
                    "UpperFilters": [],
                    "LowerFilters": [],
                }

                # UpperFilters 가져오기
                try:
                    upperfilters = winreg.QueryValueEx(guid_key, "UpperFilters")[0]
                    if isinstance(upperfilters, list):
                        device_class["UpperFilters"] = upperfilters
                    else:
                        device_class["UpperFilters"] = [upperfilters]
                except (FileNotFoundError, WindowsError):
                    pass

                # LowerFilters 가져오기
                try:
                    lowerfilters = winreg.QueryValueEx(guid_key, "LowerFilters")[0]
                    if isinstance(lowerfilters, list):
                        device_class["LowerFilters"] = lowerfilters
                    else:
                        device_class["LowerFilters"] = [lowerfilters]
                except (FileNotFoundError, WindowsError):
                    pass

                if device_class["UpperFilters"] or device_class["LowerFilters"]:
                    filter_info.append(device_class)

                winreg.CloseKey(guid_key)
            except WindowsError:
                pass

        winreg.CloseKey(class_key)
    except WindowsError as e:
        logger.error(f"오류 발생: {e}")

    return filter_info


def get_all_drivers_status():
    """시스템의 모든 드라이버 상태 가져오기"""
    drivers = {}  # 명시적으로 빈 딕셔너리로 초기화

    try:
        # 모든 드라이버 정보 가져오기 (CSV 형식)
        result = subprocess.run(
            ["driverquery", "/v", "/FO", "CSV"],
            capture_output=True,
            text=True,
            encoding="cp949",  # 한글 Windows에서 인코딩 문제 해결
        )

        if result.returncode == 0:
            # CSV 형식 결과 파싱
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:  # 헤더 행이 있는지 확인
                # 헤더 행에서 열 이름 추출
                header = lines[0].strip('"').split('","')

                # 상태 열 인덱스 찾기
                status_index = -1  # 명시적으로 -1로 초기화
                name_index = -1  # 명시적으로 -1로 초기화
                for i, col in enumerate(header):
                    if "상태" in col or "State" in col:
                        status_index = i
                    if "모듈 이름" in col or "Module Name" in col:
                        name_index = i

                if status_index != -1 and name_index != -1:
                    # 각 드라이버 정보 파싱
                    for i in range(1, len(lines)):
                        values = lines[i].strip('"').split('","')
                        if len(values) > max(status_index, name_index):
                            driver_name = values[name_index].lower()
                            status = values[status_index]

                            drivers[driver_name] = {
                                "name": driver_name,
                                "status": status,
                                "running": "running" in status.lower()
                                or "실행" in status,
                            }
    except Exception as e:
        logger.error(f"드라이버 정보 가져오기 오류: {str(e)}")

    # 기본 driverquery가 실패하면 직접 findstr 사용
    if not drivers:
        try:
            logger.info("기본 방법 실패, 대체 방법으로 드라이버 정보 가져오기 시도...")
            # 특정 드라이버 이름으로 검색
            for driver_prefix in ["hdlp", "ks", "part", "vol", "fve", "irda", "mfe"]:
                cmd = f"driverquery /v | findstr {driver_prefix}"
                result = subprocess.run(
                    cmd, capture_output=True, text=True, shell=True, encoding="cp949"
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        parts = re.split(r"\s+", line.strip(), maxsplit=4)
                        if len(parts) >= 4:
                            driver_name = parts[0].lower()
                            status = "Running" if "Running" in line else "Stopped"

                            drivers[driver_name] = {
                                "name": driver_name,
                                "status": status,
                                "running": "Running" in status,
                            }
        except Exception as e:
            logger.error(f"대체 방법 오류: {str(e)}")

    return drivers


def get_driver_file_path(driver_name):
    """드라이버 파일 경로 가져오기"""
    system_dir = os.environ.get("SystemRoot", r"C:\Windows")
    drivers_dir = os.path.join(system_dir, "System32", "drivers")
    driver_path = os.path.join(drivers_dir, driver_name)
    return driver_path if os.path.exists(driver_path) else None


def get_driver_info(file_path):
    try:
        if file_path is None or not os.path.exists(file_path):
            return None, None
        pe = pefile.PE(file_path)
        version = pe.FileInfo[0][0].StringTable[0].entries[b"FileVersion"]
        description = pe.FileInfo[0][0].StringTable[0].entries[b"FileDescription"]

        return version.decode(), description.decode()

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        logger.error(file_path)
        return None, None


def check_filter_drivers_status():
    """모든 필터 드라이버의 상태 확인"""
    print("디바이스 클래스 필터 드라이버 상태 확인 중...")
    filter_classes = get_device_classes_with_filters()

    print("시스템 드라이버 상태 가져오는 중...")
    all_drivers = get_all_drivers_status()

    if not all_drivers:
        print(
            "경고: 드라이버 정보를 가져올 수 없습니다. 관리자 권한으로 실행하고 있는지 확인하세요."
        )

    results = []

    for device_class in filter_classes:
        class_result = {
            "Class": device_class["Name"] or "Unknown",
            "GUID": device_class["GUID"],
            "UpperFilters": [],
            "LowerFilters": [],
        }

        # UpperFilters 상태 확인
        for driver in device_class["UpperFilters"]:
            driver_lower = driver.lower()
            # status 초기화 추가
            status = all_drivers.get(
                driver_lower, {"name": driver, "status": "Not Found", "running": False}
            )

            # 정확한 이름 매칭이 안되면 부분 매칭 시도
            if status["status"] == "Not Found":
                for d_name, d_info in all_drivers.items():
                    if driver_lower in d_name or d_name in driver_lower:
                        status = d_info
                        break

            # 드라이버 파일 정보 추가
            driver_file_name = driver + ".sys"  # 드라이버 파일 이름 구성
            file_path = get_driver_file_path(driver_file_name)
            status["file_exists"] = "Yes" if file_path else "No"
            version, desc = get_driver_info(file_path)
            status["file_description"] = desc
            status["file_version"] = version

            class_result["UpperFilters"].append(status)

        # LowerFilters 상태 확인
        for driver in device_class["LowerFilters"]:
            driver_lower = driver.lower()
            # status 초기화 추가
            status = all_drivers.get(
                driver_lower, {"name": driver, "status": "Not Found", "running": False}
            )

            # 정확한 이름 매칭이 안되면 부분 매칭 시도
            if status["status"] == "Not Found":
                for d_name, d_info in all_drivers.items():
                    if driver_lower in d_name or d_name in driver_lower:
                        status = d_info
                        break

            # 드라이버 파일 정보 추가
            driver_file_name = driver + ".sys"  # 드라이버 파일 이름 구성
            file_path = get_driver_file_path(driver_file_name)
            status["file_exists"] = "Yes" if file_path else "No"
            version, desc = get_driver_info(file_path)
            status["file_description"] = desc
            status["file_version"] = version

            class_result["LowerFilters"].append(status)

        results.append(class_result)

    return results


if __name__ == "__main__":
    print("Windows 필터 드라이버 상태 확인 도구 (개선판)")
    print("=" * 50)

    results = check_filter_drivers_status()

    if not results:
        print("필터 드라이버를 찾을 수 없습니다.")
    else:
        print(f"\n총 {len(results)}개의 디바이스 클래스에서 필터 드라이버 발견")

        # 결과 콘솔에 출력
        for i, result in enumerate(results, 1):
            print(f"\n{i}. 디바이스 클래스: {result['Class']} ({result['GUID']})")

            if result["UpperFilters"]:
                print("  UpperFilters:")
                for driver in result["UpperFilters"]:
                    status_icon = "✓" if driver["running"] else "✗"
                    file_status = "✓" if driver["file_exists"] == "Yes" else "✗"
                    print(
                        f"    {status_icon} {driver['name']}: {driver['status']}  파일 존재: {file_status}  설명: {driver['file_description']}"
                    )

            if result["LowerFilters"]:
                print("  LowerFilters:")
                for driver in result["LowerFilters"]:
                    status_icon = "✓" if driver["running"] else "✗"
                    file_status = "✓" if driver["file_exists"] == "Yes" else "✗"
                    print(
                        f"    {status_icon} {driver['name']}: {driver['status']}  파일 존재: {file_status}  설명: {driver['file_description']}"
                    )

        output_filename = f"filter_drivers_status_{ socket.gethostname() }.csv"
        # CSV 파일로 저장
        with open(output_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Class",
                    "GUID",
                    "FilterType",
                    "DriverName",
                    "Status",
                    "Running",
                    "FileExists",
                    "FileVersion",
                    "FileDescription",
                ]
            )

            for result in results:
                for driver in result["UpperFilters"]:
                    writer.writerow(
                        [
                            result["Class"],
                            result["GUID"],
                            "UpperFilter",
                            driver["name"],
                            driver["status"],
                            "Yes" if driver["running"] else "No",
                            driver["file_exists"],
                            driver["file_version"],
                            driver["file_description"],
                        ]
                    )

                for driver in result["LowerFilters"]:
                    writer.writerow(
                        [
                            result["Class"],
                            result["GUID"],
                            "LowerFilter",
                            driver["name"],
                            driver["status"],
                            "Yes" if driver["running"] else "No",
                            driver["file_exists"],
                            driver["file_version"],
                            driver["file_description"],
                        ]
                    )

        print(f"\n결과가 {output_filename} 파일로 저장되었습니다.")

    if os.path.getsize(log_filename) == 0:
        logger.remove()
        os.remove(log_filename)
    else:
        print(f"\n오류가 있습니다, 같은 경로에 생성된 {log_filename} 을 확인해주세요.")

    input("\nEnter를 눌러 종료하세요...")
