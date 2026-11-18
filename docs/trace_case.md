# Trace case: từ trace tới quyết định sai đầu tiên

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

## Case đã phân tích: `seeded_regression C-002@11`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11` (run ID `E-seeded_regression-20261118-ec83`, `eval_set_sha=ec836a38c870`) |
| Triệu chứng | `pass_rate` FAIL (`status resolved != denied`), `RefundAmountCorrect` FAIL (`ledger=20000 expected=0`), `DbFactKept` FAIL (`1 override event(s)`). Reply nói `"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."`; ledger ghi `refund_vnd=20000, refund_count=1` trong khi nhãn là `refund_vnd=0, refund_count=0, status=denied`. |
| Bước sai đầu tiên | Event `3 model_override {"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event `1 handoff` (giao `check_applicable_policy` với `allowed_tools` hợp lệ) và event `2 investigator` (`lookup_order` đọc đúng `order O-202` từ DB với `delay_days=2`) đều đúng. Ngay tại bước `3`, agent lấy `5 ngày` từ nội dung ticket đè lên dữ kiện DB (`2 ngày`), kéo theo bước `4 quote` tính sai `20000đ` và ghi nhận hoàn tiền sai vào ledger. |
| Failure mode | `FM-03` (`ticket_trust — tin ticket hơn DB`) |
| Đối chứng | Cùng `C-002@11` trên shape `fixed`: không có event `model_override`; bước `3` là `quote {"amount_vnd": 0, "reason": "no_entitlement", "clause_ids": [], "parts": {}}`, bước `4` là `reply` từ chối theo chính sách, ledger ghi `refund_vnd=0, refund_count=0, status=denied` (`PASS`). |
| Regression test | `test_c002_seed11_ticket_override_regression` trong [test_lab9_trace_case.py](file:///c:/Users/HAI.2021ssd/Desktop/WORK/AI20K/lab9/src/tests/test_lab9_trace_case.py) kiểm tra `DbFactKept` và `RefundAmountCorrect` (fail trên `seeded_regression`, pass trên `fixed`). |
| Chưa chắc chắn | Trace dùng `MockLLM`; chưa biết với LLM thật và cách diễn đạt mơ hồ hơn (ví dụ "trễ gần một tuần"), model có tiếp tục ghi đè không; ngoài ra nếu lỗi không ghi event `model_override` (`quiet_override`), `DbFactKept` ở mức step sẽ không thấy, phải dựa vào `RefundAmountCorrect` ở mức outcome. |
