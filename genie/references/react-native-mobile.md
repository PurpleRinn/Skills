# React Native·Expo 모바일 어댑터

`.genie/config.json`의 `frameworks.mobile`에 `react-native` 또는 `expo`가 있을 때만 이 문서를 사용한다. Expo managed·prebuild·bare React Native와 패키지 관리자를 먼저 구분한다.

## 구조와 기본 검증

- `package.json` scripts, lockfile, TypeScript, ESLint, Jest, Metro, `android/`, `ios/`, Expo 설정과 CI를 확인한다.
- 설치·검증 명령은 lockfile과 프로젝트 scripts를 우선한다. 임의로 npm과 yarn, pnpm을 섞지 않는다.
- 단위·컴포넌트 테스트는 JS 동작을 검증하지만 Swift·Objective-C·Kotlin·Java 네이티브 구현까지 보장하지 않는다.
- 핵심 흐름은 기존 Detox·Maestro·Appium 또는 프로젝트 E2E 도구를 사용해 release 성격의 빌드와 기기·시뮬레이터에서 확인한다.

## 네이티브 경계

- Native Module, Fabric Component, Codegen, CocoaPods와 Gradle 변경이 있으면 Android와 iOS 빌드를 각각 검증한다.
- 권한, 푸시, 딥링크, 백그라운드 작업과 네이티브 화면은 JS mock 결과만으로 완료 처리하지 않는다.
- React Native·Hermes·네이티브 의존성 버전 호환성과 New Architecture 적용 여부를 확인한다.

## 성능

- 개발 모드는 JS 성능 기준선으로 사용하지 않는다.
- JS thread와 UI thread 프레임, 시작 시간, 메모리, 번들 크기, 대형 목록과 네비게이션 전환을 release 빌드에서 확인한다.

## 출시

- Expo이면 EAS 또는 프로젝트에 설정된 빌드·업데이트 절차를 사용하고, bare이면 Gradle·Xcode와 CI 설정을 따른다.
- OTA가 있으면 네이티브 런타임 버전 호환성, 롤백 가능 범위와 스토어 바이너리 출시를 분리한다.
- Android applicationId·versionCode와 iOS bundle ID·build number·서명을 확인하되 Secret은 기록하지 않는다.
