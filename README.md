# TRADE OPERATIONS SUITE — 공개 업데이트 배포

**2026-10-02 17:19 KST: Master v0.1.26 / 장기 순번11 자동 검증·온라인 배포 완료.** 번역 입력·실행 연결 오류 수정과 업무 도구 등록 전환본입니다. 기존 업무 기준·Glass UI·설정·결과 보존을 유지합니다. [변경 내용](releases/v0.1.26/NOTES.md).

## 최신 상태 확인

- [자동 게시 완료 상태](publisher/status.json) — 게시 버전·순번·검증 결과·실행 기록
- [현재 Master 서명 요청](publisher/current-request.json) — ready는 승인 요청, idle는 추가 서명 불필요
- [활성 장기 서명 목록](updates/stable-longterm.signed.json)
- [자동 검증·게시 진행/실패 기록](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/actions/workflows/auto-publish-signed.yml)
- [정식 Releases](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/releases)

## Master 서명 후 자동 배포

기존 도우미 v1.1.1에서 **승인 · 서명 · 전달**을 누르면 서명 수신 → 운영 서명·요청·패키지 검증 → Windows 실제 다운로드·적용/복구 검사 → 온라인 목록 게시가 자동 진행됩니다. 대화에 완료 메시지를 입력할 필요가 없습니다. 도우미 재설치·재서명·개인키 전송은 필요 없습니다. [절차와 실패 복구](publisher/automation/README.md).

도우미의 ‘자동 전달 완료’는 접수 상태이며 서버 검증·게시 완료와 구분합니다. 검사 실패 시 새 목록을 게시하지 않습니다. 게시 후 공개 조회/Release 전환 실패는 실행 기록에 표시되며 동일 서명을 재사용해 완료 단계를 복구합니다.

## 프로그램 업데이트

기존 Master는 **최신 여부 확인 → 업데이트 다운로드 → 적용·재시작**으로 갱신합니다. 새 Setup·GitHub 로그인·토큰 입력은 필요하지 않습니다. 일반 이용자는 서명 도우미를 사용하지 않습니다.

v0.1.26은 15개 게이트 회귀 검사 및 실제 v25/v26 Windows 실행파일 총36개 검사를 통과했습니다. 무인증 실제 패키지 다운로드, 서명된 적용/복구, 합성 설정·결과 보존을 확인했습니다. 실제 사용자 PC 적용·번역 업무 확인은 별도입니다. v27 세관 검수비용 활성화는 v26 PC 전환 확인 후 준비합니다. User 정식 배포는 별도입니다.

구버전 전환 목록 `updates/stable.signed.json`의 v22/순번6은 유지합니다. 최신 승인 대상은 장기 목록이며 개발 커밋을 실행 앱에 자동 적용하지 않습니다. 기존 배포 파일은 같은 버전으로 덮어쓰지 않습니다. 공개 배포가 별도 오픈소스 라이선스 부여를 뜻하지 않으며 제3자 구성요소에는 각 라이선스가 적용됩니다.

[배포 관리 기준](DISTRIBUTION_POLICY.md)
