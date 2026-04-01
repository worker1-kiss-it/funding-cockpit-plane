import { useEffect, useState, useCallback } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { ChevronRight, File, Folder, Search, Download, FileText } from "lucide-react";
import { useProject } from "@/hooks/store/use-project";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

interface TreeNode {
  name: string;
  type: "folder" | "file";
  path: string;
  size?: number;
  children?: TreeNode[];
}

const FileTreeNode = ({ node, level, onSelect }: { node: TreeNode; level: number; onSelect: (path: string) => void }) => {
  const [expanded, setExpanded] = useState(level < 1);

  if (node.type === "folder") {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 w-full text-left py-1 px-1 hover:bg-custom-background-90 rounded text-sm"
          style={{ paddingLeft: `${level * 16 + 4}px` }}
        >
          <ChevronRight className={`size-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`} />
          <Folder className="size-3.5 shrink-0 text-custom-primary-100" />
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children?.map((child) => (
          <FileTreeNode key={child.path} node={child} level={level + 1} onSelect={onSelect} />
        ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      className="flex items-center gap-1.5 w-full text-left py-1 px-1 hover:bg-custom-background-90 rounded text-sm text-custom-text-200 hover:text-custom-text-100"
      style={{ paddingLeft: `${level * 16 + 4}px` }}
    >
      <File className="size-3.5 shrink-0" />
      <span className="truncate">{node.name}</span>
    </button>
  );
};

export const KnowledgeBaseView = observer(function KnowledgeBaseView() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const { workspaceProjectIds } = useProject();
  const projectId = workspaceProjectIds?.[0];

  const [tree, setTree] = useState<any>(null);
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<any>(null);
  const [fileType, setFileType] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!workspaceSlug || !projectId) return;
    service.getKbTree(workspaceSlug, projectId).then(setTree).catch(() => {});
  }, [workspaceSlug, projectId]);

  const openFile = useCallback(async (path: string) => {
    if (!workspaceSlug || !projectId) return;
    setCurrentPath(path);
    setFileContent(null);
    setFileType(null);
    setLoading(true);

    const ext = path.split(".").pop()?.toLowerCase() || "";
    if (ext === "pdf") {
      setFileType("pdf");
      setLoading(false);
      return;
    }
    if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(ext)) {
      setFileType("image");
      setLoading(false);
      return;
    }
    if (["docx", "xlsx", "pptx", "zip", "doc", "xls"].includes(ext)) {
      setFileType("download");
      setLoading(false);
      return;
    }

    try {
      const data = await service.getKbFile(workspaceSlug, projectId, path);
      setFileContent(data);
      setFileType(data?.file_type || "text");
    } catch {
      setFileContent({ error: "Failed to load file" });
    } finally {
      setLoading(false);
    }
  }, [workspaceSlug, projectId]);

  const handleSearch = useCallback(async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2 || !workspaceSlug || !projectId) {
      setSearchResults([]);
      return;
    }
    try {
      const data = await service.searchKb(workspaceSlug, projectId, q);
      setSearchResults(data?.results || []);
    } catch {
      setSearchResults([]);
    }
  }, [workspaceSlug, projectId]);

  const rawFileUrl = currentPath && workspaceSlug && projectId
    ? `/api/funding/workspaces/${workspaceSlug}/projects/${projectId}/funding/kb/file/raw/?path=${encodeURIComponent(currentPath)}`
    : "";

  if (!projectId) {
    return <div className="flex items-center justify-center h-full text-custom-text-300">No project found.</div>;
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar */}
      <div className="w-72 border-r border-custom-border-200 flex flex-col shrink-0">
        <div className="p-3 border-b border-custom-border-200">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-custom-background-90">
            <Search className="size-3.5 text-custom-text-300" />
            <input
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search files..."
              className="bg-transparent text-sm flex-1 outline-none text-custom-text-100 placeholder:text-custom-text-400"
            />
          </div>
        </div>

        {searchResults.length > 0 && (
          <div className="p-2 border-b border-custom-border-200 max-h-40 overflow-auto">
            <div className="text-xs text-custom-text-300 px-2 mb-1">Results</div>
            {searchResults.map((r: any) => (
              <button
                key={r.file}
                onClick={() => { openFile(r.file); setSearchQuery(""); setSearchResults([]); }}
                className="w-full text-left px-2 py-1.5 rounded hover:bg-custom-background-90 text-xs"
              >
                <div className="font-medium text-custom-primary-100 truncate">{r.file.split("/").pop()}</div>
                <div className="text-custom-text-400 truncate">{r.file}</div>
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-auto p-2">
          {tree?.items?.map((node: TreeNode) => (
            <FileTreeNode key={node.path} node={node} level={0} onSelect={openFile} />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {currentPath && (
          <div className="px-5 py-2.5 border-b border-custom-border-200 text-sm text-custom-text-300 flex items-center gap-2">
            <FileText className="size-3.5" />
            <span className="truncate">{currentPath}</span>
            {rawFileUrl && (
              <a href={rawFileUrl} download className="ml-auto text-custom-primary-100 hover:underline flex items-center gap-1">
                <Download className="size-3" /> Download
              </a>
            )}
          </div>
        )}

        <div className="flex-1 overflow-auto p-6">
          {!currentPath && (
            <div className="flex flex-col items-center justify-center h-full text-custom-text-300">
              <Folder className="size-12 mb-3 opacity-30" />
              <p>Select a file from the knowledge base</p>
            </div>
          )}

          {loading && <div className="text-center py-12 text-custom-text-300">Loading...</div>}

          {fileType === "pdf" && rawFileUrl && (
            <iframe src={rawFileUrl} className="w-full h-full border-0 rounded" style={{ minHeight: "70vh" }} />
          )}

          {fileType === "image" && rawFileUrl && (
            <img src={rawFileUrl} className="max-w-full rounded shadow" alt={currentPath || ""} />
          )}

          {fileType === "download" && rawFileUrl && (
            <div className="text-center py-16">
              <File className="size-16 mx-auto mb-4 text-custom-text-400" />
              <div className="text-custom-text-200 mb-4">{currentPath?.split("/").pop()}</div>
              <a href={rawFileUrl} download className="inline-flex items-center gap-2 px-4 py-2 bg-custom-primary-100 text-white rounded-md hover:opacity-90">
                <Download className="size-4" /> Download File
              </a>
            </div>
          )}

          {fileType === "markdown" && fileContent?.content && (
            <div className="prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: fileContent.content }} />
          )}

          {fileType === "text" && fileContent?.content && (
            <pre className="text-sm whitespace-pre-wrap text-custom-text-200">{fileContent.content}</pre>
          )}

          {fileContent?.error && (
            <div className="text-center py-12 text-red-500">{fileContent.error}</div>
          )}
        </div>
      </div>
    </div>
  );
});
