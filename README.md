# EDPL Tools

이 프로젝트는 EDPL 도구 모음을 제공합니다. 이 도구들은 Python으로 작성되었으며, PyInstaller를 사용하여 빌드됩니다.

## 파일 설명

### `collect_device_classes.py`

`collect_device_classes.py`는 디바이스 클래스들 모두 정리해줍니다.
결과는 `device_classes_{hostname}.csv` 로 저장됩니다.

### `collect_device_classes.py`

`collect_device_classes.py`는 Upper/Lower Filters 에 등록된 드라이버 상태 및 정보를 수집합니다.
결과는 `filter_drivers_status_{hostname}.csv` 로 저장됩니다.

## PyInstaller 사용법

이 프로젝트는 PyInstaller를 사용하여 실행 파일로 빌드됩니다. PyInstaller는 Python 애플리케이션을 독립 실행형 실행 파일로 패키징하는 도구입니다.

### pyi-grab_version

`pyi-grab_version`은 PyInstaller의 하위 명령어로, 실행 파일에 버전 정보를 포함시키는 데 사용됩니다. 이 명령어를 사용하여 애플리케이션의 버전 정보를 쉽게 관리할 수 있습니다.

```bash
pyi-grab_version <version_file>
```

위 명령어에서 `<version_file>`은 버전 정보가 포함된 파일을 가리킵니다.

## 빌드 방법

`build.bat`

## 기여 방법

기여를 원하시면, 풀 리퀘스트를 제출해 주세요. 버그 리포트 및 기능 요청은 이슈 트래커를 통해 제출할 수 있습니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.
