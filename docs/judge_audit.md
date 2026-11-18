# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có (tất cả ≥ ngưỡng) | **dùng** |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không (κ=0.375 < 0.6, R=0.3 < 0.7) | **loại** |

- `tone_ok` confusion: `{'tp': 24, 'fp': 4, 'fn': 6, 'tn': 66}`, fail rate quan sát `0.28` → hiệu chỉnh Rogan-Gladen `0.30`.
- `helpful` confusion: `{'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70}`, fail rate quan sát `0.09` → hiệu chỉnh Rogan-Gladen `0.30`.

## ≥5 case audit thủ công (từ `judge_tone_public.csv` và `judge_helpful_public.csv`)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | `H-008` ("Em đã hoàn tiền cho anh rồi nha, anh check giúp em.") | PASS | FAIL | Người đúng | Xưng "em" + "nha" quá suồng sã; sửa rubric: cấm từ ngữ thân mật ("nha", "nhé", xưng "em"/"bạn"). |
| 2 | `H-017` ("Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha.") | PASS | FAIL | Người đúng | Xưng "bạn ơi" + "nha" không chuẩn CSKH; sửa rubric: bắt buộc đại từ "anh/chị" + "LogiX". |
| 3 | `H-029` ("Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm.") | PASS | FAIL | Người đúng | Giọng ra lệnh ("không cần nhắn thêm") nhưng judge bị đánh lừa bởi "Dạ, vui lòng"; sửa rubric: đánh giá toàn câu, không chấm theo từ khóa mở đầu. |
| 4 | `H-042` ("Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ.") | FAIL | PASS | Người đúng | Câu ngắn gọn nhưng lịch sự, đủ thông tin; sửa rubric: thêm ví dụ câu ngắn chuẩn mực là PASS. |
| 5 | `H-051` ("Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ.") | FAIL | PASS | Người đúng | Judge phạt nhầm từ "refund"; sửa rubric: làm rõ thuật ngữ phổ thông không làm FAIL tone nếu ngữ điệu lịch sự. |
| 6 | `H-070` ("Dạ, LogiX đã hoàn 90.000đ cho đơn O-909 ạ 😂😂") | PASS | FAIL | Người đúng | Emoji cười không phù hợp giao dịch tài chính; sửa rubric: cấm emoji không trang trọng trong phản hồi hoàn tiền. |
| 7 | `HL-015` ("Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ." — ledger 40.000đ) | PASS | FAIL | Người đúng | Judge `helpful` bỏ sót hoàn toàn lỗi sai tiền vì chỉ đọc bề mặt văn bản lịch sự; không dùng judge cho số tiền, thay bằng code grader `ReplyLedgerMatch`. |

## Kết luận
- **Tiêu chí bị loại:** `helpful` (`κ=0.375`, `R=0.300`, `fn=21/30`). Dù Precision = 1.0, judge bỏ sót 70% ca lỗi thật (chủ yếu là các ca trả lời dài dòng, lịch sự nhưng báo sai số tiền so với ledger như `HL-015`, `HL-016`, `HL-020`, `HL-028`). Dùng judge này làm gate sẽ cho lọt các lỗi nghiêm trọng và làm sai lệch tỉ lệ lỗi quan sát (`0.09` vs thực tế `0.30`).
- **Tiêu chí được dùng:** `tone_ok` (`κ=0.757`, `P=0.857`, `R=0.800`) đạt cả 3 ngưỡng FLOORS, có thể dùng theo dõi chất lượng giọng văn (vẫn cần audit định kỳ và sửa rubric cho các trường hợp biên ở trên).
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
