function out = inventor_export_cad(varargin)
%INVENTOR_EXPORT_CAD  Export the RobôCIn v2025 robot meshes (chassis, wheel, kicker, dribbler) from Inventor with colours.
%
%   out = INVENTOR_EXPORT_CAD() drives Autodesk Inventor through its COM API (no manual step): it opens the
%   top-level assembly, walks the whole occurrence tree, tessellates every visible leaf body with
%   ComponentOccurrence.SurfaceBodies(i).CalculateFacets (proxies, i.e. already in the TOP-LEVEL assembly frame)
%   and writes four meshes in the dtssl MJCF body frame
%       p_mjcf [m] = R_z(+90 deg) * (p_inventor [mm] - [0 0 AxleZmm]) / 1000      (x' = -y, y' = x)
%   each as a full OBJ plus a decimated LOD OBJ (MATLAB reducepatch, part by part so colours survive):
%     ssl_chassis.obj   everything that is not a mechanism, a wheel, a fastener, a decal or a tiny SMD part
%     ssl_wheel.obj     ONE wheel sub-assembly (option 'WheelPath') in its own frame: axle along +x (outward),
%                       roller mid-plane at x = 0; the MJCF places it at (R cos phi, R sin phi, wheel.r), euler z = phi
%     ssl_kicker.obj    kicker_assembly_5mm:1 (fixed to the chassis, same frame as the chassis OBJ)
%     ssl_dribbler.obj  Dribbler_Robocup2025v3:1 (same frame)
%   Colours: every leaf gets the base (diffuse) colour of its own appearance, ComponentOccurrence.Appearance
%   (part appearance or occurrence override), which is what the Inventor viewport shows in shaded mode: an
%   override set on an ancestor sub-assembly is NOT propagated (checked on robot_v2025_v3: the cover sub-assembly
%   carries a 'green' override but is drawn black, the colour of its parts). Faces are grouped per part
%   ('g <path>') and per colour ('usemtl m_rrggbb', materials in ssl_<tag>.mtl shared by the LOD file).
%   The OBJ header records the provenance (assembly, occurrence, transform, tolerance), the decal plane of the
%   id pattern ('# id plate z'), the wheel axle data and one line per part
%       '# part <path> | lo x y z | hi x y z | mtl m_rrggbb | <appearance>'      (mm, MJCF frame)
%   from which tools/register_cad_meshes.py derives meshes.json (counts, bbox, md5, materials, cover and id-plate
%   heights, wheel axle, kicker/dribbler features: bar, chip plate, mouth, IR boards).
%
%   Name/value options:
%     'Assembly'      full path of the .iam (default ssl-mechanics\v2025\inventor\robot_v2025_v3.iam)
%     'OutDir'        output folder (default <repo>\src\dtssl\physics\assets)
%     'Targets'       cell of tags to write, subset of {'chassis','wheel','kicker','dribbler'} (default all)
%     'Mechanisms'    N x 2 cell {occurrence name, tag} (default kicker_assembly_5mm:1 / Dribbler_Robocup2025v3:1)
%     'WheelPath'     regexp on the occurrence path of the wheel sub-assembly exported as the wheel (default
%                     '/Direct_Transmission_new:1/Wheel_v2025_new:1$'); every other occurrence with the same
%                     name (the other three wheels) is left out of the chassis
%     'ToleranceCm'   chordal tolerance of CalculateFacets, Inventor units = cm (default 0.01 = 0.1 mm)
%     'SkipPattern'   regexp of leaf names NOT exported (default hardware, coil wire and SMD passives)
%     'DecalPattern'  regexp of the id-pattern decal parts, skipped but their plane recorded (default '^Papier')
%     'MinPartMm'     chassis only: leaves whose range box is smaller than this in every direction are skipped (default 4)
%     'ColourOverrides' N x 2 cell {regexp on the leaf name, [r g b]}: colour used instead of the appearance. Default:
%                     the cover part (Capa_2025_V3) is black, because in Inventor it is wrapped in a black decal with
%                     the sponsor logos (decals are images on faces, not appearances, so the API reports its grey base)
%     'FaceTargets'   struct of face budgets, fields chassis, chassis_lod, wheel, wheel_lod, kicker, kicker_lod,
%                     dribbler, dribbler_lod (0 = keep every face); default 60000/12000, 8000/1200, 0/1500, 0/3500
%     'AxleZmm'       wheel-axle plane height in the Inventor frame (default 24.15: the wheel axle of the v2025 CAD,
%                     measured on Direct_Transmission_new:1; the MJCF places the meshes at z = wheel.r above the floor)
%     'Close'         true (default) closes the assembly (no save) at the end if this call opened it; Inventor itself
%                     is quit only when this function started it (a running, signed-in instance is reused and left open)
%
%   Opening the 7.7 MB assembly loads ~330 documents and takes 1-2 min; an instance started here runs invisible.
%   Starting Inventor through COM needs a valid Autodesk sign-in session (otherwise open it by hand, sign in and
%   rerun: the running instance is reused). Run from the repo root:
%       addpath tools; out = inventor_export_cad();
%       python tools/register_cad_meshes.py
%
%   Output struct per target: tag, parts (paths), skipped, materials (name -> rgb), file, file_lod, faces, faces_lod,
%   bbox_mjcf_mm, plus id_plate_z_mm (chassis) and axle (wheel: angle_deg, centre_mm, outer_radius_mm).

ip = inputParser;
ip.addParameter('Assembly', 'C:\Users\victo\Documents\ssl-mechanics\v2025\inventor\robot_v2025_v3.iam', @ischar);
ip.addParameter('OutDir', fullfile(fileparts(fileparts(mfilename('fullpath'))), 'src', 'dtssl', 'physics', 'assets'), @ischar);
ip.addParameter('Targets', {'chassis', 'wheel', 'kicker', 'dribbler'}, @iscell);
ip.addParameter('Mechanisms', {'kicker_assembly_5mm:1', 'kicker'; 'Dribbler_Robocup2025v3:1', 'dribbler'}, @iscell);
ip.addParameter('WheelPath', '/Direct_Transmission_new:1/Wheel_v2025_new:1$', @ischar);
ip.addParameter('ToleranceCm', 0.01, @isnumeric);
ip.addParameter('SkipPattern', '^(DIN|ISO|Copper|R0805|C0805K|SOT23|LED-GULLR|1X04)', @ischar);
ip.addParameter('DecalPattern', '^Papier', @ischar);
ip.addParameter('MinPartMm', 4, @isnumeric);
ip.addParameter('ColourOverrides', {'^Part Studio 1 - Capa_2025_V3', [15 15 15]}, @iscell);
ip.addParameter('FaceTargets', struct('chassis', 60000, 'chassis_lod', 12000, 'wheel', 8000, 'wheel_lod', 1200, ...
                                      'kicker', 0, 'kicker_lod', 1500, 'dribbler', 0, 'dribbler_lod', 3500), @isstruct);
ip.addParameter('AxleZmm', 24.15, @isnumeric);
ip.addParameter('Close', true, @islogical);
ip.parse(varargin{:});
o = ip.Results;
if ~isfolder(o.OutDir), mkdir(o.OutDir); end
Rz = [0 -1 0; 1 0 0; 0 0 1];
stamp = char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm'));
wheelBase = regexprep(regexp(o.WheelPath, '[^/]+$', 'match', 'once'), '[:\\]\d*\$?$', '');

% --- Inventor session (reuse a running instance, else start one invisible) ----------------------
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

% --- walk the tree: classify every leaf, tessellate, colour ------------------------------------
% leaf record: cls (chassis|wheel|kicker|dribbler), path, V (mm, Inventor frame), F, rgb, app, box (MJCF mm)
leaves = struct('cls', {}, 'path', {}, 'V', {}, 'F', {}, 'rgb', {}, 'app', {}, 'box', {}, 'occ', {});
skipped = struct('chassis', {{}}, 'wheel', {{}}, 'kicker', {{}}, 'dribbler', {{}});
idPlateZ = [];
mechT = containers.Map();
stack = struct('occ', {}, 'path', {}, 'cls', {});
for k = 1:cdef.Occurrences.Count
    stack(end+1) = struct('occ', cdef.Occurrences.Item(k), 'path', '', 'cls', 'chassis'); %#ok<AGROW>
end
t0 = tic;
while ~isempty(stack)
    s = stack(end); stack(end) = []; occ = s.occ;
    name = occ.Name;
    path = [s.path '/' name];
    cls = s.cls;
    hit = find(strcmp(name, o.Mechanisms(:, 1)), 1);
    if ~isempty(hit)
        cls = o.Mechanisms{hit, 2};
        mechT(cls) = occ_transform(occ);
    elseif ~isempty(regexp(path, o.WheelPath, 'once'))
        cls = 'wheel';
        mechT('wheel') = occ_transform(occ);
    elseif strcmp(regexprep(name, ':\d+$', ''), wheelBase)
        continue                                              % the other wheel instances
    end
    try, if ~occ.Visible || occ.Suppressed, continue; end, catch, end
    try, n = occ.SubOccurrences.Count; catch, n = 0; end
    if n > 0
        for k = 1:n
            stack(end+1) = struct('occ', occ.SubOccurrences.Item(k), 'path', path, 'cls', cls); %#ok<AGROW>
        end
        continue
    end
    if ~isempty(regexp(name, o.DecalPattern, 'once'))
        try, b = occ.RangeBox; idPlateZ(end+1) = b.MaxPoint.Z * 10 - o.AxleZmm; catch, end %#ok<AGROW>
        continue
    end
    if ~any(strcmp(cls, o.Targets)), continue; end
    if ~isempty(regexp(name, o.SkipPattern, 'once'))
        skipped.(cls){end+1} = name; continue;
    end
    if strcmp(cls, 'chassis') && o.MinPartMm > 0
        try
            b = occ.RangeBox;
            ext = [b.MaxPoint.X - b.MinPoint.X, b.MaxPoint.Y - b.MinPoint.Y, b.MaxPoint.Z - b.MinPoint.Z] * 10;
            if max(ext) < o.MinPartMm, skipped.(cls){end+1} = name; continue; end
        catch
        end
    end
    try
        sb = occ.SurfaceBodies; nb = sb.Count;
    catch
        nb = 0;
    end
    V = zeros(0, 3); F = zeros(0, 3);
    for j = 1:nb
        try
            [~, fc, xyz, ~, idx] = sb.Item(j).CalculateFacets(o.ToleranceCm);
        catch
            fc = 0;
        end
        if fc == 0, continue; end
        P = reshape(double(xyz), 3, []).' * 10;                 % cm -> mm, top-level frame
        Fi = reshape(double(idx), 3, []).';
        F = [F; Fi + size(V, 1)]; V = [V; P]; %#ok<AGROW>
    end
    if isempty(F), continue; end
    try, ap = occ.Appearance; catch, ap = []; end
    [rgb, apName] = appearance_rgb(ap);
    for k = 1:size(o.ColourOverrides, 1)
        if ~isempty(regexp(name, o.ColourOverrides{k, 1}, 'once'))
            rgb = o.ColourOverrides{k, 2}; apName = [apName ' (override)']; break %#ok<AGROW>
        end
    end
    Lm = (Rz * (V - [0 0 o.AxleZmm]).').';
    leaves(end+1) = struct('cls', cls, 'path', path, 'V', V, 'F', F, 'rgb', rgb, 'app', apName, ...
                           'box', [min(Lm); max(Lm)], 'occ', []); %#ok<AGROW>
end
fprintf('tessellated %d leaves in %.0f s\n', numel(leaves), toc(t0));

% --- write one target at a time -----------------------------------------------------------------
out = struct('tag', {}, 'parts', {}, 'skipped', {}, 'materials', {}, 'file', {}, 'file_lod', {}, 'faces', {}, ...
             'faces_lod', {}, 'bbox_mjcf_mm', {}, 'id_plate_z_mm', {}, 'axle', {});
for ti = 1:numel(o.Targets)
    tag = o.Targets{ti};
    sel = leaves(strcmp({leaves.cls}, tag));
    if isempty(sel), warning('no parts for target %s', tag); continue; end
    extra = {};
    axle = [];
    % frame: MJCF body frame for everything; the wheel is then moved to its own axle frame
    for k = 1:numel(sel)
        sel(k).V = (Rz * (sel(k).V - [0 0 o.AxleZmm]).').' / 1000;        % m, MJCF frame
    end
    if strcmp(tag, 'wheel')
        [sel, axle] = wheel_frame(sel);
        extra{end+1} = sprintf('wheel axle: CAD angle %.3f deg from body +x (outward), centre (MJCF frame, mm) [%.3f %.3f %.3f], outer radius %.3f mm; mesh frame: axle = +x outward, roller mid-plane x = 0', ...
                               axle.angle_deg, axle.centre_mm, axle.outer_radius_mm); %#ok<AGROW>
    end
    if strcmp(tag, 'chassis') && ~isempty(idPlateZ)
        extra{end+1} = sprintf('id plate z (decal plane of the SSL pattern, MJCF frame, mm): %.3f', median(idPlateZ)); %#ok<AGROW>
    end
    if isKey(mechT, tag)
        extra{end+1} = sprintf('occurrence transform (Inventor frame, mm): %s', mat2str(mechT(tag), 6)); %#ok<AGROW>
    end
    % materials
    mtl = containers.Map();
    for k = 1:numel(sel)
        key = sprintf('m_%02x%02x%02x', round(sel(k).rgb));
        sel(k).mtl = key;
        if ~isKey(mtl, key), mtl(key) = struct('rgb', sel(k).rgb, 'app', sel(k).app); end
    end
    mtlFile = fullfile(o.OutDir, sprintf('ssl_%s.mtl', tag));
    write_mtl(mtlFile, mtl, stamp, tag);
    hdr = {sprintf('generated by tools/inventor_export_cad.m on %s; do not edit (regenerate from Inventor)', stamp), ...
           sprintf('source %s, target %s, CalculateFacets tolerance %.3f cm', doc.FullFileName, tag, o.ToleranceCm), ...
           sprintf('units m; frame = dtssl MJCF body frame (dribbler at +x, wheels at 60/135/225/300 deg); z origin at the wheel-axle plane (Inventor z = %.2f mm); place at pos = (0, 0, wheel.r)', o.AxleZmm)};
    if strcmp(tag, 'wheel')
        hdr{3} = 'units m; frame = wheel frame: axle along +x (outward radial direction of the robot), roller mid-plane at x = 0; the MJCF places it at (R cos phi, R sin phi, wheel.r) with euler z = phi';
    end
    hdr = [hdr, extra]; %#ok<AGROW>
    mk = keys(mtl);
    mline = cell(1, numel(mk));
    for k = 1:numel(mk), m = mtl(mk{k}); mline{k} = sprintf('%s=%s', mk{k}, m.app); end
    hdr{end+1} = sprintf('materials (%d): %s', numel(mk), strjoin(mline, ' | ')); %#ok<AGROW>
    hdr{end+1} = sprintf('skipped (%d): %s', numel(skipped.(tag)), strjoin(skipped.(tag), ' | ')); %#ok<AGROW>
    for k = 1:numel(sel)
        hdr{end+1} = sprintf('part %s | lo %.2f %.2f %.2f | hi %.2f %.2f %.2f | mtl %s | %s', sel(k).path, ...
                             sel(k).box(1, :), sel(k).box(2, :), sel(k).mtl, sel(k).app); %#ok<AGROW>
    end
    nfull = sum(arrayfun(@(l) size(l.F, 1), sel));
    budget = o.FaceTargets.(tag);
    selFull = sel;
    if budget > 0 && nfull > budget, selFull = decimate_parts(sel, budget); end
    nf = sum(arrayfun(@(l) size(l.F, 1), selFull));
    fn = fullfile(o.OutDir, sprintf('ssl_%s.obj', tag));
    note = sprintf('%d parts, %d faces (full resolution)', numel(sel), nfull);
    if nf < nfull, note = sprintf('%d parts, %d -> %d faces (reducepatch per part)', numel(sel), nfull, nf); end
    write_obj(fn, selFull, [hdr(1:3), {note}, hdr(4:end)], sprintf('ssl_%s.mtl', tag));
    selLod = decimate_parts(selFull, o.FaceTargets.([tag '_lod']));
    nl = sum(arrayfun(@(l) size(l.F, 1), selLod));
    fnl = fullfile(o.OutDir, sprintf('ssl_%s_lod.obj', tag));
    write_obj(fnl, selLod, [hdr(1:3), {sprintf('%d parts, %d -> %d faces (LOD for the GUI 3D views: reducepatch per part of ssl_%s.obj)', ...
                                                numel(sel), nf, nl, tag)}, hdr(4:end)], sprintf('ssl_%s.mtl', tag));
    allV = vertcat(selFull.V);
    out(end+1) = struct('tag', tag, 'parts', {{sel.path}}, 'skipped', {skipped.(tag)}, 'materials', mtl, 'file', fn, ...
        'file_lod', fnl, 'faces', nf, 'faces_lod', nl, 'bbox_mjcf_mm', [min(allV); max(allV)] * 1000, ...
        'id_plate_z_mm', median(idPlateZ), 'axle', axle); %#ok<AGROW>
    fprintf('%s: %d parts (%d skipped), %d faces (LOD %d), %d colours -> %s\n  bbox (mm): [%.1f %.1f %.1f]..[%.1f %.1f %.1f]\n', ...
        tag, numel(sel), numel(skipped.(tag)), nf, nl, numel(mk), fn, min(allV) * 1000, max(allV) * 1000);
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


function T = occ_transform(occ)
%OCC_TRANSFORM  4x4 occurrence transform in the top-level frame (translation in mm).
m = occ.Transformation; T = zeros(4);
for r = 1:4, for c = 1:4, T(r, c) = m.Cell(r, c); end, end
T(1:3, 4) = T(1:3, 4) * 10;
end


function [rgb, name] = appearance_rgb(ap)
%APPEARANCE_RGB  Base colour (0-255) and display name of an Inventor appearance asset, whatever its schema
%   (generic_diffuse, plasticvinyl_color, metal_color, ...). This is the shaded-view colour; textures are ignored.
rgb = [191 191 191]; name = '';
if isempty(ap), return; end
try, name = ap.DisplayName; catch, end
prio = {'generic_diffuse', 'plasticvinyl_color', 'metal_color', 'metal_f0', 'wallpaint_color', 'metallicpaint_base_color', ...
        'ceramic_color', 'concrete_color', 'hardwood_color', 'masonrycmu_color', 'stone_color', 'mirror_tintcolor', ...
        'solidglass_transmittance_custom_color', 'glazing_transmittance_color', 'water_tint_color'};
vals = containers.Map();
try, n = ap.Count; catch, n = 0; end
for i = 1:n
    try
        av = ap.Item(i);
        v = av.Value;
        if ~isnumeric(v) && ~ischar(v) && ~islogical(v)
            vals(av.Name) = [double(v.Red) double(v.Green) double(v.Blue)];
        end
    catch
    end
end
for k = 1:numel(prio)
    if isKey(vals, prio{k}), rgb = vals(prio{k}); return; end
end
ks = keys(vals);
for k = 1:numel(ks)
    if isempty(regexp(ks{k}, '(Tint|bump|self_illum|pattern|map)', 'once')), rgb = vals(ks{k}); return; end
end
end


function [sel, axle] = wheel_frame(sel)
%WHEEL_FRAME  Move the wheel parts (MJCF frame, m) to the wheel frame: axle +x outward, roller mid-plane at x = 0.
P = vertcat(sel.V);
c0 = mean(P);
[~, ~, U] = svd(P - c0, 0);
a = U(:, 3).';                                          % smallest extent = axle direction
a(3) = 0; a = a / norm(a);
if dot(a(1:2), c0(1:2)) < 0, a = -a; end                % outward (away from the robot centre)
phi = atan2(a(2), a(1));
isRoller = ~cellfun(@isempty, regexp({sel.path}, '/Roller', 'once'));
Pr = vertcat(sel(isRoller).V);
if isempty(Pr), Pr = P; end
s = (Pr - c0) * a.';                                    % axial coordinate of the roller vertices
cen = c0 + a * (min(s) + max(s)) / 2;                   % roller mid-plane on the axle
cen(3) = 0;                                             % the axle is on the wheel-axle plane by construction
Rm = [cos(-phi) -sin(-phi) 0; sin(-phi) cos(-phi) 0; 0 0 1];
rad = 0;
for k = 1:numel(sel)
    sel(k).V = (Rm * (sel(k).V - cen).').';
    if isRoller(k), rad = max(rad, max(hypot(sel(k).V(:, 2), sel(k).V(:, 3)))); end
end
axle = struct('angle_deg', rad2deg(phi), 'centre_mm', cen * 1000, 'outer_radius_mm', rad * 1000);
end


function sel = decimate_parts(sel, budget)
%DECIMATE_PARTS  reducepatch part by part to about `budget` faces in total (colours and groups survive).
n = arrayfun(@(l) size(l.F, 1), sel);
total = sum(n);
if budget <= 0 || total <= budget, return; end
ratio = budget / total;
for k = 1:numel(sel)
    target = max(round(n(k) * ratio), min(n(k), 24));
    if target >= n(k), continue; end
    [F, V] = reducepatch(sel(k).F, sel(k).V, target);
    sel(k).F = F; sel(k).V = V;
end
end


function write_mtl(fn, mtl, stamp, tag)
fid = fopen(fn, 'w');
cleaner = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '# generated by tools/inventor_export_cad.m on %s; diffuse colours of the Inventor appearances of ssl_%s.obj\n', stamp, tag);
ks = keys(mtl);
for k = 1:numel(ks)
    m = mtl(ks{k});
    fprintf(fid, 'newmtl %s\n# %s\nKd %.4f %.4f %.4f\nKa 0 0 0\nKs 0 0 0\n', ks{k}, m.app, m.rgb / 255);
end
end


function write_obj(fn, sel, header, mtllib)
%WRITE_OBJ  Triangles-only OBJ with '# ' header lines, one 'g' group per part and 'usemtl' per colour (LF endings).
fid = fopen(fn, 'w');
cleaner = onCleanup(@() fclose(fid)); %#ok<NASGU>
for k = 1:numel(header), fprintf(fid, '# %s\n', header{k}); end
fprintf(fid, 'mtllib %s\n', mtllib);
off = 0;
for k = 1:numel(sel), fprintf(fid, 'v %.6f %.6f %.6f\n', sel(k).V.'); end
for k = 1:numel(sel)
    fprintf(fid, 'g %s\nusemtl %s\n', regexprep(sel(k).path, '\s+', '_'), sel(k).mtl);
    fprintf(fid, 'f %d %d %d\n', (sel(k).F + off).');
    off = off + size(sel(k).V, 1);
end
end
