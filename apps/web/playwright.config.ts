import {defineConfig} from "@playwright/test";
export default defineConfig({testDir:"./tests",timeout:180000,use:{baseURL:process.env.PGO_WEB_URL||"http://localhost:3000",trace:"retain-on-failure"},reporter:"list"});
