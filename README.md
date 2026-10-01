# TRADE OPERATIONS SUITE — 공개 업데이트 배포

**현재 활성 온라인 업데이트: Master v0.1.22.** 기존 앱 전환 목록은 순번 6, v0.1.21 이상이 이용하는 장기 목록은 순번 7입니다.

- 승인 메일 모듈의 제목 편집·회사별 초안과 참조처 선택 개선.
- 기존 개인 메일 설정을 보존하며 새 승인 정책으로 전환.
- Glass Workspace, 1920×1080 기준 배치, 50~200% 확대/축소와 배율 기억 유지.
- 기존 업무 기준·선택 저장·비차단 알림·서명 업데이트 및 복구 유지.

기존 Master는 **최신 여부 확인 → 업데이트 다운로드 → 적용·재시작**으로 갱신합니다. 별도 Setup, GitHub 로그인이나 토큰 입력은 필요하지 않습니다. v0.1.17 이전 설치본은 기존 전환 경로가 필요합니다.

기존 Master 키의 두 서명과 Windows 운영 실행파일의 공개 다운로드·적용·복구·서명 이력 전환 검증을 통과했습니다. **v0.1.22 사용자 PC 적용과 실제 Outlook 확인은 대기**입니다. PC 확인 이력의 이전 버전은 v0.1.20입니다. User 정식 배포와 공개 최초 설치용 Setup은 아직 제공하지 않습니다.

개인 메일 설정·양식은 기존 PC에 보존하며 공개 패키지에 포함하지 않습니다. 새 개인 참조 정책은 Master에게 제공된 비공개 준비 절차로 적용합니다. 이 저장소에는 검사한 배포 파일과 공개용 버전 정보·서명·해시·제3자 라이선스만 게시합니다. 공개 배포가 별도 오픈소스 라이선스 부여를 뜻하지 않으며 제3자 구성요소에는 각 라이선스가 적용됩니다.

| 목록 | 대상 | 순번 | 유효기한(UTC) |
|---|---|---:|---|
| [전환 목록](updates/stable.signed.json) | v0.1.20 이전의 기존 공개 채널 앱 | 6 | 2026-12-29 00:00 |
| [장기 목록](updates/stable-longterm.signed.json) | v0.1.21 이상 | 7 | 2099-12-31 23:59:59 |

두 목록 모두 같은 Master v0.1.22 ZIP을 지정합니다. 서명 검증·패키지 크기/해시·호환 검사 및 이전 순번 거부는 유지합니다. 새 버전은 배포자가 서명하며 이용자는 서명키·GitHub 토큰을 만들거나 입력하지 않습니다.

- [Master v0.1.22 Release](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/releases/tag/v0.1.22)
- 크기: 12,448,956 bytes
- SHA-256: `630c17125ef3b5c8a05041f4c7178a9343919e179daf859f83e47d078af897ae`

[변경 내용](releases/v0.1.22/NOTES.md) · [배포 관리 기준](DISTRIBUTION_POLICY.md) · [공식 Releases](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/releases)
