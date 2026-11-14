import {test,expect} from "@playwright/test";
test("submit a real workload and inspect evidence",async({page})=>{
 await page.goto("/");
 await expect(page.getByRole("heading",{name:"Query performance",exact:true})).toBeVisible();
 await page.getByLabel("Workload",{exact:true}).selectOption("customer_lookup");
 await expect(page.getByLabel("PostgreSQL query")).toContainText("commerce.orders");
 await page.getByRole("button",{name:"Run optimization"}).click();
 await expect(page.getByText(/Session .* \| completed/)).toBeVisible({timeout:170000});
 await page.getByText("Original execution plan",{exact:true}).click();
 await expect(page.getByText("Actual rows / loop").first()).toBeVisible();
 await page.screenshot({path:"../../docs/assets/workspace-desktop.png",fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:"../../docs/assets/workspace-mobile.png",fullPage:true});
 const download=page.waitForEvent("download");
 await page.getByRole("button",{name:"Export JSON report"}).click();
 await expect((await download).suggestedFilename()).toMatch(/^optimization-/);
});
test("reject unsafe input",async({page})=>{
 await page.goto("/");
 await page.getByLabel("PostgreSQL query").fill("DELETE FROM commerce.orders");
 await page.getByRole("button",{name:"Run optimization"}).click();
 await expect(page.getByRole("alert")).toContainText("SELECT");
});
