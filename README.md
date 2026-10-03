# Master / User 통합 배포

Master/User는 같은 버전의 모듈과 기준을 공유하며, 역할별 패키지를 한 번의 서명·게시 작업으로 제공한다. 현재 요청은 [서명 요청](publisher/current-request.json), 실제 자동 게시 완료 여부는 [게시 상태](publisher/status.json)에서 확인한다. 요청 준비와 실제 운영 서명 게시, 사용자 PC 설치는 구분한다.

v0.1.35부터 두 프로필의 Beta 최초 설치본과 업데이트 패키지를 함께 검증한다. Beta 릴리스는 prerelease로 유지한다. 사용자는 별도 GitHub 로그인·토큰·등록 없이 최초 설치와 승인된 업데이트를 이용한다. 서명 도우미는 Master 전용이며 User에게 전달하지 않는다.

## 이전 배포 안내

# TRADE OPERATIONS SUITE — 공개 업데이트 배포

**2026-10-03 10:17 KST: Master v0.1.30 / 장기 순번13 자동 검증·배포 완료.** 서명 요청은 idle이며 재서명은 필요 없습니다. v0.1.27 PC에서는 아래 안내에 따라 업데이트 파일 가져오기를 한 번 진행합니다.

배포 절차 개선: 승인된 후보의 공개 준비·Windows 검사·서명 요청 게시를 공통 workflow로 연결했습니다. 공개 캐시 확인은 기존 121초 대기 실패를 수정한 뒤 실제 0.594초에 통과했습니다. [절차·검증 범위](publisher/automation/RELEASE_PREPARATION.md).

## 최신 상태 확인

- [자동 게시 완료 상태](publisher/status.json)
- [현재 Master 서명 요청](publisher/current-request.json) — ready는 서명 대기, idle는 추가 서명 불필요
- [활성 장기 서명 목록](updates/stable-longterm.signed.json)
- [자동 검증·게시 진행/실패 기록](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/actions/workflows/auto-publish-signed.yml)
- [v0.1.30 변경 내용·적용 안내](releases/v0.1.30/NOTES.md)

## Master 서명 후 자동 배포

기존 Master Signing 도우미 v1.1.1에서 **승인 · 서명 · 전달**을 누르면 운영 서명·요청·패키지 확인, 실제 Windows 적용/복구 검사를 거쳐 게시합니다. 대화에 완료 메시지를 입력할 필요가 없습니다. 새 버전의 서명 요청은 사전에 사용자의 명시적 승인을 받아야 합니다. 이번 v0.1.30은 승인되었습니다.

도우미의 자동 전달 완료는 접수이며 게시 완료와 구분합니다. 검사 실패 시 새 목록을 게시하지 않습니다. [검증·실패 복구 절차](publisher/automation/README.md).

## v0.1.27 → v0.1.30 적용

자동 게시 상태에서 v0.1.30 완료를 확인한 후 [Master 업데이트 ZIP](https://github.com/YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES/releases/download/v0.1.30/TRADE_OPERATIONS_SUITE_Master_v0.1.30.ecuss-update.zip)을 다운로드합니다. 프로그램 **업데이트 → 업데이트 파일 가져오기**에서 압축을 풀지 않은 ZIP을 선택하고 적용·재시작합니다. 중간 버전이나 새 Setup 설치는 필요 없습니다.

v0.1.27의 온라인 검사는 새 PSR 모듈을 거부하므로 이번에는 위 가져오기가 한 번 필요합니다. v0.1.30부터 서명된 모듈 등록 정보를 이용하는 누적 온라인 업데이트를 지원합니다. 서버 배포는 PC 적용·재시작을 대신하지 않습니다.

v0.1.30은 업무 도구 Glass UI 통일, ‘세관 제시 금액’ 표시, PSR 연결과 누적 업데이트 개선을 포함합니다. 기존 번역 수정과 검증·재고 기준을 유지하며 AMOVINA REVIEW18 / AMOGREEN VINA V1.0.3 기준입니다. 개별 프로젝트의 이후 버전은 자동 포함되지 않습니다. User 정식 배포는 별도입니다.

기존 구버전 전환 목록 `updates/stable.signed.json`은 유지합니다. 최신 승인 대상은 장기 목록이며 개발 커밋을 실행 앱에 자동 적용하지 않습니다. 기존 배포 파일은 같은 버전으로 덮어쓰지 않습니다. 공개 배포가 별도 오픈소스 라이선스 부여를 뜻하지 않으며 제3자 구성요소에는 각 라이선스가 적용됩니다.

[배포 관리 기준](DISTRIBUTION_POLICY.md)
