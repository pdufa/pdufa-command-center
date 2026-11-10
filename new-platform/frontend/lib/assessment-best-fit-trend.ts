/**
 * Least-squares best-fit line through a sequence of real, dated/ordered observations.
 * This is a descriptive summary of past observations, NOT an accuracy forecast.
 * No line is returned for fewer than two distinct x-values or invalid input.
 */
export type TrendObservation={x:number;y:number};
export type BestFitTrend={
  xStart:number;xEnd:number;yStart:number;yEnd:number;
  slopePerX:number;observations:number;
};
export function bestFitTrend(observations:readonly TrendObservation[]):BestFitTrend|null{
  if(observations.length<2||observations.some(p=>
    !Number.isFinite(p.x)||!Number.isFinite(p.y)||p.y<0||p.y>100))return null;
  const points=[...observations].sort((a,b)=>a.x-b.x);
  const xStart=points[0].x,xEnd=points[points.length-1].x;
  if(xEnd<=xStart)return null;
  const mx=points.reduce((a,p)=>a+p.x,0)/points.length;
  const my=points.reduce((a,p)=>a+p.y,0)/points.length;
  const covariance=points.reduce((a,p)=>a+(p.x-mx)*(p.y-my),0);
  const variance=points.reduce((a,p)=>a+(p.x-mx)**2,0);
  if(!(variance>0)||!Number.isFinite(covariance))return null;
  const slopePerX=covariance/variance;
  const yStart=my+slopePerX*(xStart-mx);
  const yEnd=my+slopePerX*(xEnd-mx);
  if(!Number.isFinite(yStart)||!Number.isFinite(yEnd))return null;
  return {xStart,xEnd,yStart,yEnd,slopePerX,observations:points.length};
}
