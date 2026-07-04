# Hillstone Firewall Bruno Requests

Use the existing login request first. Because this Hillstone account appears to allow only one active login, avoid logging in repeatedly while testing in the web console.

After login, copy these values from `result[0]` into `environments/local.bru`:

- `token`
- `role`
- `vsysId`
- `fromrootvsys`
- `username`

Recommended flow:

1. Run `01 Query Addrbook`.
2. Find `xdr_soar_in_v4` and copy its current `member` list.
3. Update `02 Block IP PUT Array` so the body contains every existing `member` plus the new `{{targetIp}}/32`.
4. Run `02 Block IP PUT Array`.
5. Run `01 Query Addrbook` again to confirm the new member exists.

`03 Block IP PUT Named URL` is a fallback candidate. In the 2026-07-04 operator-role test it returned `success:true` but did not change the address book.
