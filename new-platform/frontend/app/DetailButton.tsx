"use client";

import { useRef, useState } from "react";
import DetailSheet, { type DetailItem } from "./DetailSheet";

export default function DetailButton({ item }: { item: DetailItem }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  return <>
    <button type="button" className="secondary" ref={trigger} aria-haspopup="dialog" onClick={() => setOpen(true)}>DETAILS</button>
    {open && <DetailSheet item={item} onClose={() => { setOpen(false); trigger.current?.focus(); }} />}
  </>;
}
