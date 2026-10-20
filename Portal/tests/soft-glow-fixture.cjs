// Shared static stylesheet fixture for browser regressions.
const fs=require('node:fs'),path=require('node:path');
module.exports=route=>{
 if(new URL(route.request().url()).pathname==='/soft-glow.css')
  return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(__dirname,'../web/soft-glow.css'))});
 return false;
};
