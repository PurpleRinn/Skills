---
name: genie-mobile-design-review
description: Genie의 빌드된 모바일 UI·UX 검토 스킬. 사용자가 "지니, 모바일 디자인 리뷰해줘", "Flutter 화면을 실제 기기 기준으로 봐줘", "React Native 앱의 접근성과 플랫폼 느낌을 점검해줘", "출시 전 UI를 검토해줘"라고 요청할 때 사용한다. Android·iOS 화면을 플랫폼 관습, 상태, 터치, 키보드, 반응형과 접근성 기준으로 평가한다.
---

# Genie Mobile Design Review

계획 문서가 아니라 실행 가능한 앱 화면을 증거로 검토하라. 사용자가 수정을 명시하지 않으면 코드를 변경하지 마라.

## 절차

1. `.genie/config.json`의 모바일 프레임워크, 대상 플랫폼과 경로를 확인하고 해당 모바일 어댑터 참고 문서를 읽어라.
2. 핵심 사용자 흐름의 모든 화면과 로딩·빈 상태·오류·성공 상태를 캡처하라.
3. 정보 계층, 간격, 타이포그래피, 색상, 터치 영역, 키보드 회피, 안전 영역, 제스처와 네비게이션을 검토하라.
4. Android Material과 iOS 관습을 무조건 동일하게 만들지 말고 각 플랫폼에서 자연스러운지 평가하라.
5. 큰 글자, 화면 읽기, 대비, 의미 레이블, 포커스 순서와 모션 감소를 확인하라.
6. 각 항목을 0~10으로 평가하고 7 미만은 증거, 사용자 영향과 권장 수정안을 제시하라.

Flutter이면 `../../references/flutter-mobile.md`, React Native 또는 Expo이면 `../../references/react-native-mobile.md`를 사용하라. 직접 호출이면 `../../references/worker-contract.md`에 따라 `docs/genie/mobile-design-review`에 기록하라.
