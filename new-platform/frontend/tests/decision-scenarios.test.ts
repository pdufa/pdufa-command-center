import assert from "node:assert/strict";
import test from "node:test";
import { evaluateDecisionScenario } from "../lib/decision-scenarios.ts";
const baseline={asOf:"2026-10-26T12:00:00Z",currentPrice:10,approvalProbability:0.7,approvalPrice:16,rejectionPrice:4,delayProbability:0.1,delayPrice:8,roundTripCostPct:1,sourceVerified:true,calibrated:true};
test("three-outcome expected price and costs",()=>{const r=evaluateDecisionScenario(baseline);assert.equal(r.status,"RESEARCH_ONLY");assert.ok(Math.abs(r.expectedPrice!-12.8)<1e-9);assert.ok(Math.abs(r.expectedReturnPct!-27)<1e-9);});
test("unverified source fails closed",()=>{const r=evaluateDecisionScenario({...baseline,sourceVerified:false});assert.equal(r.status,"NOT_READY");assert.equal(r.expectedPrice,null);});
test("uncalibrated probability fails closed",()=>assert.equal(evaluateDecisionScenario({...baseline,calibrated:false}).status,"NOT_READY"));
test("probabilities cannot exceed one",()=>assert.equal(evaluateDecisionScenario({...baseline,delayProbability:0.4}).status,"NOT_READY"));
test("invalid prices fail closed",()=>assert.equal(evaluateDecisionScenario({...baseline,rejectionPrice:0}).status,"NOT_READY"));
