import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { Button } from "@mui/material";

interface Config {
  first_seen: string | null;
  last_seen: string | null;
  module: string;
  resource: string;
  id: number | string | null;
}

async function fetch_table_data(id: string) {
  const response = await fetch("/api/config/" + id);
  const resource: Config = await response.json();
  return resource;
}

function SingleConfigView() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [rawData, setRawData] = useState({});
  const [resource, setResource] = useState("");
  useEffect(() => {
    if (id === undefined) {
      return;
    }
    fetch_table_data(id).then((data) => {
      setRawData(data);
      setResource(data.resource);
    });
  }, [id]);
  return (
    <>
      <h1>Config: { resource } ({ id })</h1>
      <pre className="code-block"><code>
        { JSON.stringify(rawData, null, 2) }
      </code></pre>
      <Button fullWidth variant="outlined"
          onClick={() => {
            navigate("./");
          }}
        >Back</Button>
    </>
  );
}

export default SingleConfigView;
