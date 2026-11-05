/** Read-only RAAS FDA three-way research accuracy scorecard.
 * Never accepts client-submitted forecasts or promotes ratings.
 */
import {currentRaasFdaThreeWayResearchScorecard}
 from "../../../lib/raas-fda-three-way-research-scorecard";
export const dynamic="force-dynamic";
export function GET(){
 const scorecard=currentRaasFdaThreeWayResearchScorecard();
 return Response.json(scorecard,{headers:{
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
