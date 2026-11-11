import WtAlpacaStatusSheet from "../../WtAlpacaStatusSheet";

export const metadata={
  title:"WT Status · Alpaca technical metrics",
  description:"Source-dated read-only Alpaca BUY/WAIT metric status sheets for SVRA and CAPR.",
};

/** Pure research; authenticated Alpaca endpoints verify each exact Program ID. */
export default function WtStatusPage(){
  return <WtAlpacaStatusSheet/>;
}
