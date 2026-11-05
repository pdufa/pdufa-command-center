/** Research-only, read-only audit of the currently saved FDA forecast
 * receipt metadata. Never returns approved accuracy or trading signals.
 */
import {currentRaasFdaForecastFreezeReceiptAudit}
 from "../../../lib/raas-fda-forecast-freeze-receipt-audit";
export const dynamic="force-dynamic";
export function GET(){
 const audit=currentRaasFdaForecastFreezeReceiptAudit();
 return Response.json(audit,{headers:{
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
