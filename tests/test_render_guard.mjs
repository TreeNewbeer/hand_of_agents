import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const moduleUrl = new URL("../src/hand_of_agents/web/render-guard.js", import.meta.url);
const moduleSource = await readFile(moduleUrl, "utf8");
const { createRenderGuard } = await import(
  `data:text/javascript,${encodeURIComponent(moduleSource)}`
);

test("a pending render waits until after the pointer click task", () => {
  const scheduledTasks = [];
  let renderCount = 0;
  const guard = createRenderGuard(
    () => { renderCount += 1; },
    () => false,
    (callback) => scheduledTasks.push(callback),
  );

  guard.beginInteraction("pointer:1");
  assert.equal(guard.requestRender(), false);
  guard.endInteraction("pointer:1");

  assert.equal(renderCount, 0);
  assert.equal(scheduledTasks.length, 1);
  scheduledTasks.shift()();
  assert.equal(renderCount, 1);
});

test("ending one of multiple interactions does not render early", () => {
  const scheduledTasks = [];
  let renderCount = 0;
  const guard = createRenderGuard(
    () => { renderCount += 1; },
    () => false,
    (callback) => scheduledTasks.push(callback),
  );

  guard.beginInteraction("pointer:1");
  guard.beginInteraction("pointer:2");
  guard.requestRender();
  guard.endInteraction("pointer:1");
  scheduledTasks.shift()();
  assert.equal(renderCount, 0);

  guard.endInteraction("pointer:2");
  scheduledTasks.shift()();
  assert.equal(renderCount, 1);
});

test("an active native select keeps a pending render deferred", () => {
  const scheduledTasks = [];
  let selectActive = true;
  let renderCount = 0;
  const guard = createRenderGuard(
    () => { renderCount += 1; },
    () => selectActive,
    (callback) => scheduledTasks.push(callback),
  );

  guard.beginInteraction("pointer:1");
  guard.requestRender();
  guard.endInteraction("pointer:1");
  scheduledTasks.shift()();
  assert.equal(renderCount, 0);

  selectActive = false;
  guard.flush();
  assert.equal(renderCount, 1);
});
