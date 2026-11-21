I’ve put together **Paper Vianden**, a small disposable SOC range for smoke-testing
our agent setup:

https://github.com/SegmondFault/paper-vianden

It runs a simulated corporate network with normal traffic, a scripted intrusion,
real Suricata alerts, searchable logs, case notes and handovers.

For the basic blue smoke test, an operator starts the default exercise and shares
the host and blue SSH credentials privately. Once they confirm it is ready,
connect our agent’s SSH tool as `vianden-agent-blue@HOST`. You can check the
connection with:

```sh
ssh vianden-agent-blue@HOST 'hostname'
ssh vianden-agent-blue@HOST 'analyst inbox'
```

Give the agent this task:

> Investigate suspicious activity using the alert inbox and logs. Open a case,
> record supporting evidence and notes, and produce a handover.

Participants only need their role’s SSH login. The operator handles the
reservation code, traffic modes, exports and cleanup.

[Participant quickstart](https://github.com/SegmondFault/paper-vianden/blob/main/QUICKSTART.md)
· [Operator quickstart](https://github.com/SegmondFault/paper-vianden/blob/main/OPERATOR_QUICKSTART.md)
