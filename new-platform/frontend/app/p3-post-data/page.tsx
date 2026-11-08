import {permanentRedirect} from "next/navigation";

/** Retired legacy display alias; the only active trial roster is FOCUS. */
export default function RetiredP3PostDataPage(){
  permanentRedirect("/focus");
}
