SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwE-zsX0D_zE0L3hkmUV9IkWKLVbSS24khntToqKLUuiK0M-RBD1KWbCrxI7aI6peKt/exec"
TOKEN = "CHANGE-MOI-123"

function doGet(e) {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  const values = sheet.getDataRange().getValues();
  const headers = values.shift();
  const data = values.map(r => {
    let obj = {};
    headers.forEach((h, i) => obj[h] = r[i]);
    return obj;
  });
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents || "{}");
  if (body.token !== TOKEN) {
    return ContentService.createTextOutput("Unauthorized")
      .setMimeType(ContentService.MimeType.TEXT);
  }

  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  sheet.appendRow([
    body.night,
    body.room,
    body.bed,
    body.name,
    new Date().toISOString()
  ]);

  return ContentService.createTextOutput("OK")
    .setMimeType(ContentService.MimeType.TEXT);
}



