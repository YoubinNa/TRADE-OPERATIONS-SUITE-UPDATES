# Master Signing Assistant v1.1.1

[최종 도우미 ZIP](TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1.zip) · 18,830 bytes · SHA-256 `dd146f56b1da1f1b289d8ee5a58a676054d8805c9bf5160e01090d0ec5209a4f`

최초 한 번 압축 해제 → Install-Publisher.cmd 실행 → 기존 Master Signing 바로가기 실행 → 전달 연결 설정.
GitHub fine-grained 토큰은 이 배포 저장소만 선택하고 Contents: Read and write를 부여합니다. Metadata는 기본 제공이며 Workflows나 다른 저장소 권한은 필요 없습니다. 토큰은 도우미에만 직접 입력하고 현재 Windows 사용자 DPAPI로 암호화 저장합니다. 만료·회수 시에만 다시 연결합니다.

이후에는 **도우미 실행 → 자동 조회된 내용 확인 → 승인·서명·전달 한 번**입니다. 공개 서명 결과만 수신함에 저장하고 동일 내용 재조회 후 성공을 표시합니다. 대화에 붙여넣기·파일 전달을 생략합니다. 실패 시 서명을 보존하여 다시 전달합니다. 결과 수신과 검증 후 활성 배포는 별도 상태입니다.

Windows 58개 검사 및 [실제 GitHub 전달 7개 검사](ONLINE_VERIFICATION.json)를 통과했습니다. 실제 네트워크 검사에는 이미 공개된 v24 서명과 CI 한시적 권한만 사용했습니다. Master 개인키를 사용하거나 활성 목록을 변경하지 않았습니다. 2026-10-01 17:51 KST Master PC의 v1.1.1 실행·기존 키 인식·게시 연결 저장과 GitHub 게시 권한 확인을 완료했습니다. 신규 버전의 서명부터 자동 전달·활성화까지 전체 PC 흐름은 다음 승인 배포에서 확인합니다.

일반 User는 도우미를 설치하거나 게시 권한을 입력하지 않습니다. 기존 앱 업데이트는 계속 로그인·토큰 없이 사용합니다. v1.1.0은 검토 이력이며 최종 사용본은 v1.1.1입니다.
