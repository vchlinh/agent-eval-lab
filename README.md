# Agent Evaluation Lab

A project exploring how to rigorously test AI coding agents — not just whether they "seem to work," but whether they actually work, measured with real statistics.

## The idea

AI agents that write and fix code are everywhere now, but most demos just show a cherry-picked success story. This project builds a small testing harness that runs an AI agent through ~20 coding tasks in a sandboxed environment, checks its work against hidden tests, and reports results with proper confidence intervals — the same kind of rigor you'd expect from a real experiment, not a highlight reel.

The AI agent itself is intentionally simple. The interesting engineering work is in the *measurement*: how do you fairly and reliably tell if one setup is actually better than another?

## Status

Just getting started.

## Why

This is also a hands-on way to learn core AI/ML evaluation concepts (sandboxing, statistical testing, bias-aware comparisons) by building the tooling from scratch rather than just reading about it.
