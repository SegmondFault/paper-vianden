I’ve put together **Paper Vianden**, a small disposable SOC range for smoke-testing
our agent setup:

https://github.com/SegmondFault/paper-vianden

It runs a simulated corporate network with normal traffic, a scripted intrusion,
real Suricata alerts, searchable logs, case notes and handovers.

Get the VPS address and SSH credentials privately; replace `HOST` below.
One human reserves the exercise:

```sh
ssh vianden@HOST 'range claim YOUR_NAME --minutes 120'
```

**This command prints the reservation code in the response’s `token` field.**
Copy that complete value into `RESERVATION_CODE` below. The current option
`--token` accepts this reservation code:

```sh
ssh vianden@HOST 'range start --token RESERVATION_CODE --seed 42 --clock-speed 60'
ssh vianden@HOST 'range status'
```

Once the phase is `ready`, connect our agent’s SSH tool as
`vianden-agent-blue@HOST` and give it this task:

> Investigate suspicious activity using `analyst inbox` and `analyst logs`.
> Open a case, record supporting evidence and notes, and produce a handover.

The human keeps the reservation code; the blue agent only needs its SSH login.
The default runs scripted malicious and normal traffic. Afterwards, the human
exports the results and releases the reservation using the same code.

[Quickstart, including the example response and cleanup commands](https://github.com/SegmondFault/paper-vianden/blob/main/QUICKSTART.md)
