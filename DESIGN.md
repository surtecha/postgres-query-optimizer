# Interface

The interface serves SQL investigation. A fixed left navigation gives access to
sessions and the workspace. The workspace places the query above the current
experiment, followed by candidate evidence. Native controls and expandable plan
rows support keyboard access. Failure states preserve the submitted SQL.

Tokens: background #0d1117, surface #151b23, border #303946, text #e6edf3,
secondary #a4b1c1, accent #72d5bb, failure #ff9e9e. Body text uses a system sans
stack. SQL and numeric measurements use a monospace stack. Spacing follows a
4px base with 24px section gaps. Controls use 6px corners and a 40px target height.
Motion is limited to native disclosure behavior. Mobile layouts stack the query,
session list and plan comparison. Measurements always display units.
