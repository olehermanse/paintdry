import { useState, useEffect } from "react";
import type {} from "@mui/x-data-grid/themeAugmentation";

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
      <h1>Config:</h1>
      <pre className="code-block">
        <code>{JSON.stringify(rawData, null, 2)}</code>
      </pre>
    </>
  );
}

export default ConfigView;
