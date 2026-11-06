/**
 * Screen recording v4 — pacing driven by the narration durations.
 * Reads .tmp/rec3/durations.json so each scene stays on screen long enough.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const WS = 'D:\\KUN_lswes';
const OUT = path.join(WS, '.tmp', 'rec3');
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE = 'http://127.0.0.1:8000';

const durations = JSON.parse(fs.readFileSync(path.join(OUT, 'durations.json'), 'utf8'));
const durOf = (label) => (durations.find((d) => d.label === label) || { seconds: 5 }).seconds;

const timeline = [];
let t0 = 0;
const mark = (label) => timeline.push({ label, t: Number(((Date.now() - t0) / 1000).toFixed(2)) });

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--hide-scrollbars', '--force-device-scale-factor=1'],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1440, height: 900 } },
    locale: 'ko-KR',
  });
  const page = await context.newPage();
  const wait = (ms) => page.waitForTimeout(ms);
  const hold = async (label, extra = 0.5) => {
    mark(label);
    await wait(Math.round((durOf(label) + extra) * 1000));
  };

  t0 = Date.now();

  // 1. intro
  mark('intro');
  await page.goto(`${BASE}/?lang=ko`, { waitUntil: 'networkidle' });
  await wait(Math.round((durOf('intro') + 0.8) * 1000));

  // 2. list
  await hold('list', 1.0);

  // 3. filter
  const linkChip = page.getByRole('button', { name: '신청 링크만' });
  if (await linkChip.count()) await linkChip.first().click();
  await hold('filter', 0.8);
  await page.getByRole('button', { name: '전체' }).first().click().catch(() => {});
  await wait(700);

  // 4. search
  const search = page.locator('input[placeholder*="검색"]').first();
  if (await search.count()) {
    await search.click();
    await search.type('장학', { delay: 60 });
  }
  await hold('search', 0.8);
  await page.getByRole('button', { name: 'clear' }).first().click().catch(() => {});
  await wait(600);

  // 5. detail
  await page.goto(`${BASE}/?lang=ko&notice=knu-real-02`, { waitUntil: 'networkidle' });
  await wait(900);
  await hold('detail', 1.0);

  // 6. apply card
  const apply = page.getByText('신청 정보', { exact: false }).first();
  if (await apply.count()) await apply.scrollIntoViewIfNeeded();
  await hold('apply', 1.0);

  // 7. attachments / gallery
  const hwpTab = page.getByRole('button', { name: /첨부파일/ }).first();
  if (await hwpTab.count()) await hwpTab.click();
  await hold('attachments', 0.9);

  // 8. AI agent + email
  const agentTab = page.getByRole('button', { name: /AI 에이전트/ }).first();
  if (await agentTab.count()) await agentTab.click();
  await wait(800);
  await hold('agent', 0.8);
  const gen = page.getByRole('button', { name: /생성/ }).first();
  if (await gen.count()) {
    await gen.click();
    await wait(6500);
  }
  await hold('email', 1.0);
  await page.getByText('제목:', { exact: false }).first().scrollIntoViewIfNeeded().catch(() => {});
  await wait(600);

  // 9. assistant
  const ball = page.locator('button[title="ZeroNotice AI"]').first();
  if (await ball.count()) {
    await ball.click();
    await wait(900);
    await hold('assistant', 0.8);
    const box = page.locator('textarea').last();
    await box.click();
    await box.type('이번 주 마감 공지 알려줘', { delay: 35 });
    await page.keyboard.press('Enter');
    await wait(7500);
    await hold('assistant-answer', 0.9);
    await page.locator('section header button').last().click().catch(() => {});
    await wait(700);
  }

  // 10. subscription
  const summaryTab = page.getByRole('button', { name: /AI 요약/ }).first();
  if (await summaryTab.count()) {
    await summaryTab.click();
    await wait(900);
  }
  const sub = page.getByText('마감 알림', { exact: false }).first();
  if (await sub.count()) await sub.scrollIntoViewIfNeeded();
  await hold('subscription', 0.9);
  const toggle = page.getByRole('button', { name: /알림 받기|알림 구독 중/ }).first();
  if (await toggle.count()) await toggle.click();
  await hold('subscribed', 0.9);

  // 11. profile
  const nameField = page.locator('input[type="text"]').first();
  if (await nameField.count()) await nameField.click();
  await hold('profile', 0.9);

  // 12. repo
  await page.goto('https://github.com/stewenmc-boop/ZeroNotice', { waitUntil: 'domcontentloaded' });
  await wait(600);
  await hold('repo', 0.9);
  await page.mouse.wheel(0, 520);
  await wait(1200);

  // 13. AGENTS.md
  await page.goto('https://github.com/stewenmc-boop/ZeroNotice/blob/main/AGENTS.md', { waitUntil: 'domcontentloaded' });
  await wait(700);
  await hold('agents-md', 0.9);
  await page.mouse.wheel(0, 520);
  await wait(1200);

  // 14. commits
  await page.goto('https://github.com/stewenmc-boop/ZeroNotice/commits/main', { waitUntil: 'domcontentloaded' });
  await wait(600);
  await hold('commits', 1.0);

  // 15. summary
  const summary = 'file:///' + path.join(WS, 'docs', 'demo_summary.html').replace(/\\/g, '/');
  await page.goto(summary, { waitUntil: 'domcontentloaded' });
  await wait(800);
  await hold('summary', 1.4);
  mark('end');

  const video = await page.video().path();
  await context.close();
  await browser.close();

  fs.writeFileSync(path.join(OUT, 'timeline.json'), JSON.stringify({ timeline, video }, null, 2));
  console.log(JSON.stringify({ video, total: timeline[timeline.length - 1].t, marks: timeline.length }));
})().catch((err) => {
  console.error('REC FAILED', err);
  process.exit(1);
});
