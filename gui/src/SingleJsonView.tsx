import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { Button } from "@mui/material";

interface Resource {
  first_seen: string | null;
  last_seen: string | null;
  modules: string[];
  resource: string;
  id: number | string | null;
  source: string | null;
}

async function fetch_table_data(api: string, id: string) {
  const response = await fetch(api.endsWith("/") ? api + id : api + "/" + id);
  const resource: Resource = await response.json();
  return resource;
}

function SingleJsonView({ api }: { api: string }) {
  const navigate = useNavigate();
  const { id } = useParams();
  const [rawData, setRawData] = useState({});
  useEffect(() => {
    if (id === undefined) {
      return;
    }
    fetch_table_data(api, id).then((data) => {
      setRawData(data);
    });
  }, [api, id]);
  return (
    <>
      <h1>Details:</h1>
      <pre className="code-block">
        <code>{JSON.stringify(rawData, null, 2)}</code>
      </pre>
      <Button
        fullWidth
        variant="outlined"
        onClick={() => {
          navigate("..", { relative: "path" });
        }}
      >
        Back
      </Button>
    </>
  );
}

export default SingleJsonView;
