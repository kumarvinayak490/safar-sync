const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("/Users/vin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "docs", "pitch", "tripos-client-pitch.html");
const pdfPath = path.join(root, "docs", "pitch", "tripos-client-pitch.pdf");
const qaDir = path.join(root, ".scratch", "pitch-render");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 816, height: 1056 }, deviceScaleFactor: 2 });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
  await page.emulateMedia({ media: "print" });

  const report = await page.evaluate(() => {
    return Array.from(document.querySelectorAll(".page")).map((node, index) => {
      const rect = node.getBoundingClientRect();
      return {
        page: index + 1,
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        scrollHeight: Math.round(node.scrollHeight),
        clientHeight: Math.round(node.clientHeight),
        overflowing: node.scrollHeight > node.clientHeight + 2,
      };
    });
  });

  const overflow = report.filter((item) => item.overflowing);
  if (overflow.length > 0) {
    console.error(JSON.stringify(report, null, 2));
    throw new Error("Pitch page content overflows the fixed PDF page size.");
  }

  const pages = page.locator(".page");
  const count = await pages.count();
  for (let i = 0; i < count; i += 1) {
    await pages.nth(i).screenshot({
      path: path.join(qaDir, `tripos-client-pitch-page-${i + 1}.png`),
    });
  }

  await page.pdf({
    path: pdfPath,
    width: "8.5in",
    height: "11in",
    margin: { top: "0", right: "0", bottom: "0", left: "0" },
    printBackground: true,
    preferCSSPageSize: true,
  });

  await browser.close();
  console.log(pdfPath);
  console.log(JSON.stringify(report));
}

main().catch(async (error) => {
  console.error(error);
  process.exit(1);
});
