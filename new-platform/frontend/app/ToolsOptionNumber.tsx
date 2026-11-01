import {toolsOptionCode} from "../lib/tools-option-code";
import styles from "./ToolsOptionNumber.module.css";
export default function ToolsOptionNumber({level,index,total}:{level:number;index:number;total:number}){
  return <span className={styles.circle} aria-label={"Option "+(index+1)+" of "+total+" at level "+level}
    title={"Level "+level+", choice "+(index+1)+" of "+total}>
    {toolsOptionCode(level,index,total)}
  </span>;
}
