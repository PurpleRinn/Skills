---
name: genie-mobile-release
description: Genie의 프레임워크 중립 Android·iOS 출시 스킬. 사용자가 "지니, 모바일 출시 준비해줘", "Flutter 앱을 TestFlight와 Play 내부 테스트에 올려줘", "React Native 앱 버전과 서명을 점검해줘", "스토어 단계적 출시를 추적해줘"라고 요청할 때 사용한다. 프로젝트에 설정된 빌드·서명·테스트 트랙·스토어 절차를 실행하고 버전과 릴리스 식별자를 기록한다.
---

# Genie Mobile Release

Git 출하와 웹·백엔드 배포를 모바일 스토어 출시와 구분하라. 스토어 제출, 외부 테스터 공개와 운영 단계 승격은 명시된 승인 범위에서만 수행하라.

## 준비

1. `.genie/config.json`, `.genie/deploy.json`, 프로젝트 배포 문서와 최신 `genie-ship`, `genie-mobile-qa-only` 기록을 확인하라.
2. Flutter이면 `../../references/flutter-mobile.md`, React Native 또는 Expo이면 `../../references/react-native-mobile.md`를 읽고 Android·iOS 대상, Expo·OTA와 네이티브 빌드 여부를 확인하라.
3. 앱 버전, Android versionCode, iOS build number, 환경·flavor와 source commit을 고정하라.
4. 서명 파일이나 인증 값을 문서에 저장하지 말고 Secret 참조와 인증 상태만 확인하라.

## 실행

1. 설정된 정적 분석, 테스트와 릴리스 빌드를 실행하라.
2. 산출물의 앱 ID, 환경, 버전, 서명과 포함된 source commit을 확인하라.
3. 내부 테스트 → 제한 테스트 → 단계적 운영 출시 순서를 프로젝트 설정대로 적용하라.
4. OTA가 있으면 네이티브 바이너리 호환 범위와 OTA 릴리스를 별도 식별자로 기록하라.
5. 스토어 제출 결과, 빌드 ID, 트랙, 심사 상태와 롤아웃 비율을 수집하고 후속 `genie-mobile-canary`를 권장하라.

직접 호출이면 `../../references/worker-contract.md`에 따라 `docs/genie/mobile-release`에 기록하라.
