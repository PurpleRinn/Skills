# 웹 프레임워크 어댑터

`.genie/config.json`의 `frameworks.web`과 `capabilities`를 기준으로 적용한다. React 여부만으로 웹을 판정하지 말고 실제 브라우저 entrypoint, `react-dom`, Vue·Nuxt, Svelte·SvelteKit, Angular, Astro, Remix, Next와 빌드 설정을 확인한다.

## 공통

- package manager와 `package.json` scripts, lockfile, CI의 build·lint·typecheck·test 명령을 우선한다.
- 브라우저 QA는 프레임워크와 무관하게 핵심 사용자 흐름, 접근성, 네트워크·콘솔 오류와 반응형을 확인한다.

## 렌더링 형태

- SPA: 라우팅, 인증·권한, 새로고침, 코드 분할과 API 실패 상태를 확인한다.
- SSR: 서버·클라이언트 결과 불일치, hydration, 캐시, 서버 로그와 런타임 환경을 확인한다.
- SSG·정적 사이트: 생성 경로, 링크, SEO 메타데이터, sitemap과 배포 산출물을 확인한다.
- PWA: service worker 갱신, 오프라인, 캐시 무효화와 이전 버전 사용자의 업데이트 흐름을 확인한다.

프레임워크 이름이 같아도 렌더링·배포 형태가 다르면 검증이 달라진다. `capabilities`에 기록된 `ssr`, `pwa`, `offline`, `role-based-access`만 조건부 검증으로 추가한다.
