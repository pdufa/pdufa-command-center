import {permanentRedirect} from "next/navigation";

/** Historical URL only: the P3 POST-DATA spreadsheet identity is retired. */
export default function RetiredP3PostDataAlias(){
 permanentRedirect("/focus");
}
