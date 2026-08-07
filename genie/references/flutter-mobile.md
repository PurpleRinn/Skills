# Flutter 모바일 어댑터

`.genie/config.json`의 `frameworks.mobile`에 `flutter`가 있을 때만 이 문서를 사용한다. 프로젝트의 실제 스크립트와 버전 고정을 우선하고 명령을 추측해 의존성을 추가하지 않는다.

## 구조와 기본 검증

- `pubspec.yaml`, Flutter·Dart SDK 제약, flavor, `lib/`, `test/`, `integration_test/`, `android/`, `ios/`를 확인한다.
- 기본 후보는 `flutter pub get`, `dart format --output=none --set-exit-if-changed`, `flutter analyze`, `flutter test`이지만 프로젝트 문서와 CI 명령을 우선한다.
- Widget 테스트는 컴포넌트 동작, `integration_test`는 실제 앱 흐름에 사용한다.
- 권한 대화상자, 푸시, 딥링크, 플랫폼 뷰처럼 OS UI가 포함되면 기존 Patrol·네이티브 테스트·기기 테스트 구성을 찾는다.

## 기기 QA

- `flutter devices`로 대상과 OS를 고정하고 debug와 release/profile 결과를 혼동하지 않는다.
- Android 뒤로가기, iOS 제스처, 키보드, 안전 영역, 권한, 앱 수명주기, 오프라인·재연결을 확인한다.
- 접근성 테스트에서는 semantics, 큰 글자, 대비와 Android·iOS 터치 영역을 확인한다.

## 성능

- 성능 판단은 profile 또는 release 성격의 빌드에서 수행한다.
- DevTools의 프레임, CPU, 메모리, 네트워크와 앱 크기를 사용하고 debug JIT 결과를 기준선으로 저장하지 않는다.

## 출시

- 프로젝트 flavor와 환경별 entrypoint를 확인한다.
- Android는 app bundle·서명·applicationId·versionCode, iOS는 archive·bundle ID·서명·build number를 확인한다.
- Secret과 인증서는 기록하지 않고 안전한 저장소의 참조만 남긴다.
