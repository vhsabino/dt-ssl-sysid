function out = inventor_export_mechanisms(varargin)
%INVENTOR_EXPORT_MECHANISMS  Export the kicker and dribbler meshes of the RobôCIn v2025 robot from Inventor, in the dtssl frame.
%
%   out = INVENTOR_EXPORT_MECHANISMS() drives Autodesk Inventor through its COM API (no manual step): it
%   opens the top-level assembly, finds the requested occurrences by name anywhere in the tree, tessellates
%   every visible leaf body with ComponentOccurrence.SurfaceBodies(i).CalculateFacets (proxies, i.e. already
%   in the TOP-LEVEL assembly frame = the frame of usd/wheel/robot_chasis.usd and of
%   cad/chasis_simplified_Simplify_2.stp) and writes, per mechanism, one full OBJ plus one decimated LOD OBJ
%   (MATLAB reducepatch) in the dtssl MJCF body frame:
%       p_mjcf [m] = R_z(+90 deg) * (p_inventor [mm] - [0 0 AxleZmm]) / 1000     (x' = -y, y' = x)
%   so the files are placed exactly like ssl_chassis.obj: geom pos = (0, 0, wheel.r). Visual-only meshes.
%   The OBJ header records the provenance (assembly, occurrence, transform, tolerance, parts kept/skipped) and
%   one '# part <path> | lo x y z | hi x y z' line (mm, MJCF frame) per leaf part, from which
%   tools/usd_to_mjcf_meshes.py --register-mechanisms derives the entries of meshes.json (counts, bbox, md5,
%   dribbler bar axis, kicker plunger axes).
%
%   Name/value options (defaults = the 2026-10-06 run):
%     'Assembly'    full path of the .iam (default ssl-mechanics\v2025\inventor\robot_v2025_v3.iam)
%     'Targets'     N x 3 cell {occurrence name, tag, LOD face target}; default
%                   {'kicker_assembly_5mm:1', 'kicker', 1500; 'Dribbler_Robocup2025v3:1', 'dribbler', 3500}
%     'OutDir'      output folder (default <repo>\src\dtssl\physics\assets)
%     'ToleranceCm' chordal tolerance of CalculateFacets, Inventor units = cm (default 0.01 = 0.1 mm)
%     'SkipPattern' regexp of leaf names NOT exported (default hardware, coil wire and SMD passives)
%     'AxleZmm'     wheel-axle plane height in the Inventor frame (default 24.15, see tools/usd_to_mjcf_meshes.py)
%     'Close'       true (default) closes the assembly (no save) at the end; Inventor itself is quit only when this
%                   function started it (a running, signed-in instance is reused and left open)
%
%   Opening the 7.7 MB assembly loads ~330 documents and takes 1-2 min; an instance started here runs invisible.
%   Requires MATLAB on the same Windows machine as Inventor (2025/2026). Run from the repo root:
%       addpath tools; out = inventor_export_mechanisms();
%       python tools/usd_to_mjcf_meshes.py --register-mechanisms
%   Validated 2026-10-06 (Inventor 2026.1, MATLAB R2026a): kicker 12 parts / 4990 faces, dribbler 32 parts / 14862 faces.
%
%   Output struct per target: name, tag, T (4x4 occurrence transform, mm, Inventor frame), parts, skipped,
%   bbox_mm (Inventor frame), bbox_mjcf_mm, file, file_lod, faces, faces_lod.

ip = inputParser;
ip.addParameter('Assembly', 'C:\Users\victo\Documents\ssl-mechanics\v2025\inventor\robot_v2025_v3.iam', @ischar);
ip.addParameter('Targets', {'kicker_assembly_5mm:1', 'kicker', 1500; 'Dribbler_Robocup2025v3:1', 'dribbler', 3500}, @iscell);
ip.addParameter('OutDir', fullfile(fileparts(fileparts(mfilename('fullpath'))), 'src', 'dtssl', 'physics', 'assets'), @ischar);
ip.addParameter('ToleranceCm', 0.01, @isnumeric);
ip.addParameter('SkipPattern', '^(DIN|ISO|Copper|R0805|C0805K|SOT23|LED-GULLR|1X04)', @ischar);
ip.addParameter('AxleZmm', 24.15, @isnumeric);
ip.addParameter('Close', true, @islogical);
ip.parse(varargin{:});
o = ip.Results;
if ~isfolder(o.OutDir), mkdir(o.OutDir); end
Rz = [0 -1 0; 1 0 0; 0 0 1];
stamp = char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm'));

% --- Inventor session (reuse a running instance, else start one invisible) ----------------------
% Starting Inventor through COM needs a valid Autodesk sign-in session; without one the new process
% crashes at start-up ("Autodesk Error Report"). If that happens, open Inventor by hand, sign in, keep it
% open with no document and run this again: the running instance is reused.
try
    inv = actxGetRunningServer('Inventor.Application'); owned = false;
catch
    inv = actxserver('Inventor.Application'); owned = true;
    inv.Visible = false;
end
inv.SilentOperation = true;
doc = []; opened = false;
for k = 1:inv.Documents.Count
    if strcmpi(inv.Documents.Item(k).FullFileName, o.Assembly), doc = inv.Documents.Item(k); break; end
end
if isempty(doc)
    t0 = tic; doc = inv.Documents.Open(o.Assembly, false); opened = true;
    fprintf('opened %s in %.0fs\n', o.Assembly, toc(t0));
end
cdef = doc.ComponentDefinition;

% --- find the target occurrences anywhere in the tree -------------------------------------------
found = cell(size(o.Targets, 1), 1);
stack = {};
for k = 1:cdef.Occurrences.Count, stack{end+1} = cdef.Occurrences.Item(k); end %#ok<AGROW>
while ~isempty(stack)
    occ = stack{end}; stack(end) = [];
    hit = find(strcmp(occ.Name, o.Targets(:, 1)), 1);
    if ~isempty(hit), found{hit} = occ; continue; end
    try, n = occ.SubOccurrences.Count; catch, n = 0; end
    for k = 1:n, stack{end+1} = occ.SubOccurrences.Item(k); end %#ok<AGROW>
end

out = struct('name', {}, 'tag', {}, 'T', {}, 'parts', {}, 'skipped', {}, 'bbox_mm', {}, 'bbox_mjcf_mm', {}, ...
             'file', {}, 'file_lod', {}, 'faces', {}, 'faces_lod', {});
for ti = 1:size(o.Targets, 1)
    root = found{ti};
    if isempty(root), warning('occurrence %s not found', o.Targets{ti, 1}); continue; end
    tag = o.Targets{ti, 2}; lodTarget = o.Targets{ti, 3};
    m = root.Transformation; T = zeros(4); for r = 1:4, for c = 1:4, T(r, c) = m.Cell(r, c); end, end; T(1:3, 4) = T(1:3, 4) * 10;
    V = zeros(0, 3); F = zeros(0, 3); parts = {}; partBox = zeros(0, 6); skipped = {};
    stack = struct('occ', root, 'path', '');
    while ~isempty(stack)
        s = stack(end); stack(end) = []; occ = s.occ;
        try, n = occ.SubOccurrences.Count; catch, n = 0; end
        if n > 0
            for k = 1:n, stack(end+1) = struct('occ', occ.SubOccurrences.Item(k), 'path', [s.path '/' occ.Name]); end %#ok<AGROW>
            continue
        end
        if ~isempty(regexp(occ.Name, o.SkipPattern, 'once')) || ~occ.Visible || occ.Suppressed
            skipped{end+1} = occ.Name; continue; %#ok<AGROW>
        end
        sb = occ.SurfaceBodies; Vleaf = zeros(0, 3);
        for j = 1:sb.Count
            [~, fc, xyz, ~, idx] = sb.Item(j).CalculateFacets(o.ToleranceCm);
            if fc == 0, continue; end
            P = reshape(double(xyz), 3, []).' * 10;              % cm -> mm, top-level frame
            Fi = reshape(double(idx), 3, []).';                   % 1-based triangle indices
            F = [F; Fi + size(V, 1)]; V = [V; P]; Vleaf = [Vleaf; P]; %#ok<AGROW>
        end
        if isempty(Vleaf), continue; end
        Lm = (Rz * (Vleaf - [0 0 o.AxleZmm]).').';
        parts{end+1} = [s.path '/' occ.Name]; partBox(end+1, :) = [min(Lm) max(Lm)]; %#ok<AGROW>
    end
    Vm = (Rz * (V - [0 0 o.AxleZmm]).').' / 1000;
    hdr = {sprintf('generated by tools/inventor_export_mechanisms.m on %s; do not edit (regenerate from Inventor)', stamp), ...
           sprintf('source %s, occurrence %s, CalculateFacets tolerance %.3f cm', doc.FullFileName, root.Name, o.ToleranceCm), ...
           sprintf('units m; frame = dtssl MJCF body frame (dribbler at +x, wheels at 60/135/225/300 deg); z origin at the wheel-axle plane (Inventor z = %.2f mm); place at pos = (0, 0, wheel.r)', o.AxleZmm), ...
           sprintf('occurrence transform (Inventor frame, mm): %s', mat2str(T, 6)), ...
           sprintf('skipped (%d): %s', numel(skipped), strjoin(skipped, ' | '))};
    for k = 1:numel(parts)
        hdr{end+1} = sprintf('part %s | lo %.2f %.2f %.2f | hi %.2f %.2f %.2f', parts{k}, partBox(k, 1:3), partBox(k, 4:6)); %#ok<AGROW>
    end
    fn = fullfile(o.OutDir, sprintf('ssl_%s.obj', tag));
    write_obj(fn, Vm, F, [hdr(1:4), {sprintf('%d parts, %d faces (full resolution)', numel(parts), size(F, 1))}, hdr(5:end)]);
    [Fl, Vl] = reducepatch(F, Vm, min(1.0, lodTarget / size(F, 1)));
    fnl = fullfile(o.OutDir, sprintf('ssl_%s_lod.obj', tag));
    write_obj(fnl, Vl, Fl, [hdr(1:4), {sprintf('%d parts, %d -> %d faces (LOD for the GUI 3D views: reducepatch of ssl_%s.obj)', ...
                                             numel(parts), size(F, 1), size(Fl, 1), tag)}, hdr(5:end)]);
    out(end+1) = struct('name', root.Name, 'tag', tag, 'T', T, 'parts', {parts}, 'skipped', {skipped}, ...
        'bbox_mm', [min(V); max(V)], 'bbox_mjcf_mm', [min(Vm); max(Vm)] * 1000, 'file', fn, 'file_lod', fnl, ...
        'faces', size(F, 1), 'faces_lod', size(Fl, 1)); %#ok<AGROW>
    fprintf('%s: %d parts (%d skipped), %d faces (LOD %d) -> %s\n  bbox MJCF (mm): [%.1f %.1f %.1f]..[%.1f %.1f %.1f]\n', ...
        tag, numel(parts), numel(skipped), size(F, 1), size(Fl, 1), fn, min(Vm) * 1000, max(Vm) * 1000);
end

if o.Close
    try
        if opened, doc.Close(true); end                       % SkipSave
        if owned, inv.Documents.CloseAll(false); inv.Quit(); end
    catch e
        warning('closing Inventor: %s', e.message);
    end
end
end


function write_obj(fn, V, F, header)
%WRITE_OBJ  Single-object, triangles-only OBJ with '# ' header lines (6-decimal metres), LF line endings.
fid = fopen(fn, 'w');
cleaner = onCleanup(@() fclose(fid));
for k = 1:numel(header), fprintf(fid, '# %s\n', header{k}); end
fprintf(fid, 'v %.6f %.6f %.6f\n', V.');
fprintf(fid, 'f %d %d %d\n', F.');
end
