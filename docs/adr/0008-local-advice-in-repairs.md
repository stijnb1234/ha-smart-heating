# Advice from local rules, offered through Home Assistant Repairs

Smart Heating finds wasteful patterns with explainable rules and statistics on its own daily
summaries, and offers them to the administrator as Home Assistant Repairs with an optional,
undoable Apply. Nothing is changed automatically and no data leaves the home. A trained model needs
far more data than one home gives in a few weeks, and an LLM adds an external dependency and cannot
be tested the same way. Dashboard buttons were rejected because standard cards (ADR-0005) handle a
changing list badly, and a custom panel because of the frontend code to maintain.
