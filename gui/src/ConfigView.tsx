import { useState, useEffect } from "react";
import type {} from "@mui/x-data-grid/themeAugmentation";
import CodeBlock from "./CodeBlock";

async function fetch_table_data() {
  const response = await fetch("/api/config");
  const resource = await response.json();
  return resource;
}

function ConfigView() {
  const [rawData, setRawData] = useState({});
  useEffect(() => {
    fetch_table_data().then((data) => {
      setRawData(data);
    });
  }, []);
  return (
    <>
      <p>
        The code block below shows the contents of{" "}
        <code>config/config.json</code>. There is also some "config" in{" "}
        <code>config/secrets.json</code>, but we don't want to expose that, for
        obvious reasons.{" "}
      </p>
      <CodeBlock code={JSON.stringify(rawData, null, 2)} />
    </>
  );
}

export default ConfigView;
