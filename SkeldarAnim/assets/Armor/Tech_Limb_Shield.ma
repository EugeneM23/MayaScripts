//Maya ASCII 2027 scene
//Name: Tech_Limb_Shield.ma
//Last modified: Thu, Oct 01, 2026 06:52:19 PM
//Codeset: 1252
requires maya "2027";
currentUnit -l centimeter -a degree -t ntsc;
fileInfo "application" "maya";
fileInfo "product" "Maya 2027";
fileInfo "version" "2027";
fileInfo "cutIdentifier" "202607171511-52c21617ee";
fileInfo "osv" "Windows 11 Pro v2009 (Build: 26200)";
fileInfo "UUID" "0FE756E1-44F5-99CE-EF02-F7A8B7F46184";
createNode transform -n "TechLimbShield";
	rename -uid "113A9221-4571-5F41-55B8-189C2DD3FE5F";
createNode joint -n "Root" -p "TechLimbShield";
	rename -uid "2D00D975-404A-AF55-557D-7BBE8C2237FA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 2;
createNode joint -n "Main" -p "Root";
	rename -uid "69799602-4232-0339-FEF6-729864FC247A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 19.328449249267578 -2.381844758987425 7.836517333984375 ;
	setAttr ".r" -type "double3" 77.303555830030774 187.42557679135535 10.544508996700007 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_020" -p "Main";
	rename -uid "4E9377A8-4FE7-F92E-0CFC-0D8E6FB8EEAB";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 27.614379882812514 2.2410759925842267 21.471607208251964 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 27.614380000000001 21.471606999999999 -2.2410760000000001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_019" -p "Main";
	rename -uid "C743FF49-43E2-F33E-E6B2-E09AB038BFE7";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 32.143218994140646 2.1627259254455549 13.838022232055671 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 32.143219000000002 13.838022 -2.1627260000000001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_018" -p "Main";
	rename -uid "2BB4A06C-450B-50EB-5661-29BA8FFEC945";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 34.427425384521477 2.1213779449462855 6.3767971992492694 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 34.427424999999999 6.3767969999999998 -2.121378 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_017" -p "Main";
	rename -uid "F86B839A-4B27-5723-AE18-EC8BA74343B6";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 34.898628234863295 2.1008749008178711 -1.9743069410324148 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 34.898628000000002 -1.974307 -2.1008749999999998 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_016" -p "Main";
	rename -uid "A5B9142D-4D1E-F5D5-A22A-248E32D3B39E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 33.341682434082017 2.0146379470825178 -10.602084159851083 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 33.341681999999999 -10.602084 -2.0146380000000002 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_015" -p "Main";
	rename -uid "02EA4D90-44A4-34FC-557B-CD953336B742";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 29.906246185302749 1.9114550352096558 -18.245141983032237 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 29.906245999999999 -18.245142000000001 -1.9114549999999999 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_014" -p "Main";
	rename -uid "8B52E3ED-47F6-11D9-B78A-58908CA753C9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 24.603687286376957 1.8319629430770838 -25.028238296508793 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 24.603687000000001 -25.028238000000002 -1.831963 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_013" -p "Main";
	rename -uid "C22D01D3-4EB3-FB35-6084-6EB11854F0FA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 16.763134002685547 1.7637829780578613 -30.747531890869162 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 16.763134000000001 -30.747532 -1.7637830000000001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_012" -p "Main";
	rename -uid "BA4E18DE-4158-ACE1-400F-1E999E8FAECD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 6.9746809005737305 1.6563600301742571 -34.391983032226577 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 6.9746810000000004 -34.391983000000003 -1.6563600000000001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_011" -p "Main";
	rename -uid "6060262E-4083-4098-3E5D-198A14F024D4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.7684319019317662 1.5127049684524518 -34.805732727050795 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -3.7684319999999998 -34.805732999999996 -1.512705 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_010" -p "Main";
	rename -uid "CDDBD044-47CC-6E61-10E8-EDAF1A98DD71";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -13.814380645751964 1.4711359739303624 -32.14257049560549 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -13.814380999999999 -32.142569999999999 -1.471136 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_009" -p "Main";
	rename -uid "40A16912-4541-F0FF-F148-5EA98A42D8AB";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -22.042953491210955 1.4029109477996808 -27.109785079956072 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -22.042953000000001 -27.109784999999999 -1.402911 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_008" -p "Main";
	rename -uid "5E774168-40FF-460B-AD29-CE9F551F7A88";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -28.723920822143572 1.2993719577789289 -19.588726043701172 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -28.723921000000001 -19.588726000000001 -1.299372 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_007" -p "Main";
	rename -uid "0C181618-482C-F3D9-A1E4-E3A1893E552A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -33.321636199951215 1.4509439468383789 -10.329468727111818 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -33.321635999999998 -10.329469 -1.450944 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_006" -p "Main";
	rename -uid "67CCBE71-4429-58BD-4F3D-F8AF31CB7369";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -34.846767425537138 1.4548579454421979 -0.76490300893783214 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -34.846767 -0.764903 -1.454858 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_005" -p "Main";
	rename -uid "39E55970-4730-1AA2-54EE-20AF58BE7209";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -33.664348602294936 1.4924390316009521 8.6544494628906357 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -33.664349000000001 8.6544489999999996 -1.4924390000000001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_004" -p "Main";
	rename -uid "736B6506-4574-E705-30E8-2D9090386C7B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -30.092540740966815 1.6587920188903809 17.568264007568363 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -30.092541000000001 17.568263999999999 -1.658792 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_003" -p "Main";
	rename -uid "E2053447-46D2-000A-16EA-43B46942BFEC";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -24.680913925170916 1.8051300048828125 24.582872390747081 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -24.680914000000001 24.582871999999998 -1.8051299999999999 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_002" -p "Main";
	rename -uid "46FE5F84-4D0D-5F3D-8B35-959D17967458";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -17.320613861083988 1.9066669940948469 30.235025405883803 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -17.320613999999999 30.235025 -1.9066669999999999 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_001" -p "Main";
	rename -uid "31F86772-440E-7163-1E33-A1A518E36631";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 20.29483795166016 2.1295180320739728 28.366350173950213 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 20.294837999999999 28.366350000000001 -2.129518 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_021" -p "Main";
	rename -uid "3974F018-4ED6-7A2D-1CEC-CD8F595D9570";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 16.668508529663089 -9.6415166854858416 8.0662784576416069 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 16.668509 8.0662780000000005 9.6415170000000003 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_022" -p "Main";
	rename -uid "26833099-4665-3BA4-6269-53B0F1CB4F14";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.11023139953614 -9.8511476516723615 3.943789958953857 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 18.110230999999999 3.9437899999999999 9.8511480000000002 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_023" -p "Main";
	rename -uid "ADF6BAAC-4679-0B66-B3A6-AD8D442A5CF1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -18.167266845703136 -10.21252918243408 -0.14135399460792497 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -18.167266999999999 -0.14135400000000001 10.212529 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_024" -p "Main";
	rename -uid "DD4BA14E-44A9-2158-DEA0-ECB41EFC2398";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -17.628541946411151 -10.173566818237306 4.3510961532592809 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -17.628541999999999 4.3510960000000001 10.173567 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_025" -p "Main";
	rename -uid "E4576E7C-4332-4B75-F00F-EF803287C236";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -1.3722189664840734 -10.203542709350584 -18.231430053710948 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -1.3722190000000001 -18.23143 10.203543 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_026" -p "Main";
	rename -uid "5B9C97F3-4733-64D8-843A-E1BFF83BA05C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -6.6871562004089355 -10.237472534179689 -16.998468399047855 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -6.6871559999999999 -16.998467999999999 10.237473 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_027" -p "Main";
	rename -uid "B3CEC32C-4ECF-9C9B-4ACD-C5AA44631D22";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -11.421525955200199 -10.246186256408693 -14.212967872619634 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -11.421526 -14.212968 10.246186 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_028" -p "Main";
	rename -uid "E64664A4-4FDA-5249-7AF0-9F915457B1EB";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -15.025189399719249 -10.233384132385256 -10.37619209289551 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -15.025188999999999 -10.376192 10.233383999999999 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_029" -p "Main";
	rename -uid "24E8281F-425E-BD93-E0F6-78AAD66841DA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -17.484621047973622 -10.228182792663569 -5.0230832099914586 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -17.484621000000001 -5.0230829999999997 10.228183 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_030" -p "Main";
	rename -uid "99554BF2-4B7D-E270-443D-55AF1118B33C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.0030250549316388 -10.178517341613768 -17.909624099731456 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 4.0030250000000001 -17.909624000000001 10.178516999999999 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_031" -p "Main";
	rename -uid "0B5087B3-4F57-072F-D827-C0A8AC50C839";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 12.715505599975586 -9.9995679855346662 -13.486854553222662 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 12.715506 -13.486855 9.999568 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_032" -p "Main";
	rename -uid "7B50D951-4FBE-4D84-4CF2-E79D43433FE5";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 8.6368827819824237 -10.077096939086916 -16.305444717407234 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 8.6368829999999992 -16.305444999999999 10.077097 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_033" -p "Main";
	rename -uid "2DC27F33-4F45-676D-3A7D-0E8EC331F397";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.534330368041996 -9.8708057403564471 -0.79496902227401867 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 18.534330000000001 -0.79496900000000004 9.870806 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_034" -p "Main";
	rename -uid "D22FE8DD-4388-50A1-52A0-379FFB13074D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 17.626440048217781 -9.9140224456787092 -5.7825088500976598 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 17.626439999999999 -5.7825090000000001 9.9140219999999992 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_035" -p "Main";
	rename -uid "E21404EC-4B22-61CA-45BC-27804C535CED";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 15.665007591247567 -9.8610439300537127 -9.9405622482299876 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 15.665008 -9.9405619999999999 9.8610439999999997 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "joint_on_vertex_036" -p "Main";
	rename -uid "505578AC-4C56-3F46-F77D-EC96A26E3A64";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -15.923618316650408 -9.9222469329834002 8.8678941726684677 ;
	setAttr ".r" -type "double3" 89.999999999999986 2.9930474661704551e-15 -2.4773330649198417e-15 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -15.923617999999999 8.8678939999999997 9.9222470000000005 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode transform -n "TechLimbShieldMesh" -p "TechLimbShield";
	rename -uid "BC0FC0CE-463F-DEBF-C377-EDA4F44465E5";
	setAttr ".r" -type "double3" -90 0 0 ;
	setAttr ".it" no;
createNode mesh -n "TechLimbShieldMeshShape" -p "TechLimbShieldMesh";
	rename -uid "A3A3857D-48E6-7C7D-B376-23A7C89B3A53";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "DiffuseUV";
	setAttr ".cuvs" -type "string" "DiffuseUV";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".ccls" -type "string" "colorSet0";
	setAttr ".clst[0].clsn" -type "string" "colorSet0";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr ".ndt" 0;
	setAttr ".vcs" 2;
createNode mesh -n "TechLimbShieldMeshShapeOrig" -p "TechLimbShieldMesh";
	rename -uid "F16F85CD-4FF5-3666-53A9-DBB7A963F554";
	setAttr -k off ".v";
	setAttr ".io" yes;
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".gtag[0].gtagnm" -type "string" "skinCluster1";
	setAttr ".gtag[0].gtagcmp" -type "componentList" 1 "vtx[0:406]";
	setAttr ".uvst[0].uvsn" -type "string" "DiffuseUV";
	setAttr -s 407 ".uvst[0].uvsp";
	setAttr ".uvst[0].uvsp[0:249]" -type "float2" 0.46394387 0.19775569 0.44654578
		 0.73555768 0.4449189 0.78755665 0.47452247 0.24702716 0.43565547 0.68752217 0.44654578
		 0.73555768 0.34079108 0.55795127 0.39920622 0.45131773 0.34269199 0.54833454 0.056773722
		 0.26263964 0.039660007 0.73688442 0.063973971 0.31838274 0.05235501 0.6822139 0.085888155
		 0.37124062 0.077675454 0.63590473 0.11820441 0.41206849 0.16333716 0.44589537 0.11410469
		 0.59789765 0.38762641 0.43367583 0.34079108 0.55795127 0.33859941 0.56820703 0.33694804
		 0.5743888 0.43061468 0.39143169 0.38432044 0.60785091 0.45814526 0.34599662 0.4154256
		 0.64616281 0.47175449 0.29987144 0.43565547 0.68752217 0.35953727 0.3097747 0.45814526
		 0.34599662 0.45814526 0.34599662 0.35953727 0.3097747 0.35375413 0.30655795 0.35375413
		 0.30655795 0.35953727 0.3097747 0.3616811 0.28369749 0.36821866 0.28482401 0.45814526
		 0.34599662 0.3616811 0.28369749 0.47175449 0.29987144 0.47175449 0.29987144 0.36389723
		 0.25816762 0.36389723 0.25816762 0.35879201 0.23218954 0.37049851 0.25776929 0.35879201
		 0.23218954 0.34764931 0.2102266 0.47452247 0.24702716 0.47452247 0.24702716 0.46394387
		 0.19775569 0.3648183 0.22943413 0.46394387 0.19775569 0.44228175 0.15097928 0.44228175
		 0.15097928 0.41045165 0.11236638 0.34764931 0.2102266 0.35334781 0.2057575 0.41045165
		 0.11236638 0.36420035 0.078820348 0.36420035 0.078820348 0.33616677 0.18580663 0.33184594
		 0.19104195 0.33498147 0.22013521 0.33498147 0.22013521 0.32225776 0.20272577 0.33165002
		 0.22278023 0.33165002 0.22278023 0.32915506 0.22465831 0.32915506 0.22465831 0.3169761
		 0.20899934 0.3169761 0.20899934 0.31460753 0.21184617 0.3192986 0.20625955 0.31460753
		 0.21184617 0.30048591 0.22670919 0.30168638 0.19836009 0.30292419 0.1953913 0.30048591
		 0.22670919 0.30449542 0.19139272 0.29016525 0.2199195 0.29016525 0.2199195 0.300239
		 0.20190382 0.27721569 0.21448594 0.27721569 0.21448594 0.28179958 0.19456601 0.26183951
		 0.21295196 0.26183951 0.21295196 0.24671258 0.21688533 0.28232142 0.19086605 0.24671258
		 0.21688533 0.23381008 0.22538811 0.28286311 0.18725556 0.23381008 0.22538811 0.22064081
		 0.20974934 0.22064081 0.20974934 0.20569682 0.2255159 0.23897749 0.19793874 0.26020381
		 0.19230461 0.25972611 0.18859249 0.23746873 0.19441658 0.25931016 0.1854133 0.21819393
		 0.20679271 0.23616035 0.19133484 0.28359386 0.18275082 0.20569682 0.2255159 0.20259155
		 0.22330779 0.20259155 0.22330779 0.21605365 0.20421296 0.19997323 0.22148168 0.19997323
		 0.22148168 0.21321462 0.20080817 0.19615972 0.21868169 0.19615972 0.21868169 0.2342481
		 0.18699014 0.18406415 0.20968527 0.18406415 0.20968527 0.20322628 0.18883365 0.17137605
		 0.23855829 0.17137605 0.23855829 0.17860946 0.20565963 0.16806555 0.26474369 0.16806555
		 0.26474369 0.17134865 0.28834188 0.17134865 0.28834188 0.18121473 0.31336254 0.1615596
		 0.26412106 0.18121473 0.31336254 0.16489536 0.23645437 0.16485393 0.28947496 0.17542924
		 0.31663811 0.17542924 0.31663811 0.085888155 0.37124062 0.056773722 0.26263964 0.085888155
		 0.37124062 0.063973971 0.31838274 0.063973971 0.31838274 0.056773722 0.26263964 0.06523817
		 0.20407653 0.06523817 0.20407653 0.09227211 0.14870101 0.09227211 0.14870101 0.13186905
		 0.10318279 0.13186905 0.10318279 0.19885086 0.18354404 0.18106082 0.072784781 0.18106082
		 0.072784781 0.22557043 0.16713965 0.2402173 0.056728005 0.2402173 0.056728005 0.30463105
		 0.057767928 0.22824802 0.17325526 0.25585982 0.15968746 0.30463105 0.057767928 0.25675288
		 0.16619873 0.28655645 0.16122097 0.31288913 0.17006618 0.28565764 0.16782308 0.25873572
		 0.18084759 0.31032088 0.17664313 0.34269199 0.54833454 0.39820629 0.5853681 0.34079108
		 0.55795127 0.39329821 0.59363711 0.33859941 0.56820703 0.4370659 0.6312474 0.38779813
		 0.60260153 0.33694804 0.5743888 0.38432044 0.60785091 0.4291954 0.63670236 0.4596557
		 0.67713594 0.42066592 0.64259696 0.4154256 0.64616281 0.45090455 0.68098235 0.4711926
		 0.73081303 0.44145238 0.68508452 0.43565547 0.68752217 0.46218133 0.7326147 0.47044384
		 0.78807735 0.45247233 0.73450118 0.44654578 0.73555768 0.46106294 0.78798956 0.45658413
		 0.84202617 0.45098826 0.78781819 0.4449189 0.78755665 0.4472574 0.83911961 0.42891669
		 0.89204633 0.43723795 0.83592671 0.42086917 0.88668644 0.38370663 0.93734682 0.43118823
		 0.83386976 0.37767431 0.93015844 0.32381174 0.97173727 0.4121497 0.88081682 0.32028997
		 0.96262103 0.25446424 0.98535156 0.37108791 0.92223322 0.40696529 0.87725997 0.44228175
		 0.15097928 0.46394387 0.19775569 0.25373575 0.97588867 0.18647818 0.97863728 0.3164579
		 0.9526667 0.18843974 0.9693296 0.12748818 0.95464361 0.25295338 0.96556193 0.3671895
		 0.91745156 0.13209534 0.94616479 0.076628089 0.91295755 0.19062231 0.95911604 0.082907252
		 0.90592766 0.31414261 0.94658244 0.25248566 0.95937562 0.13711664 0.93693459 0.19193754
		 0.95310372 0.2402173 0.056728005 0.18106082 0.072784781 0.14009759 0.93151695 0.30463105
		 0.057767928 0.13186905 0.10318279 0.36420035 0.078820348 0.41045165 0.11236638 0.41463012
		 0.10778373 0.366799 0.073288739 0.44750962 0.14805639 0.42564553 0.095718145 0.30554605
		 0.0517869 0.37353629 0.058635235 0.23937622 0.050429463 0.30792969 0.035696745 0.17841184
		 0.067315876 0.23709103 0.033863127 0.31085449 0.017605484 0.38250732 0.04057616 0.23418103
		 0.014648438 0.43894067 0.082167566 0.47905451 0.13039505 0.17137712 0.053223133 0.16293094
		 0.034843326 0.46165082 0.14043927 0.50479889 0.18582982 0.46973652 0.19602799 0.48567319
		 0.1913085 0.44654578 0.73555768 0.47452247 0.24702716 0.49673131 0.24715269 0.51648426
		 0.24752498 0.47995746 0.24751312 0.43565547 0.68752217 0.47175449 0.29987144 0.49388036
		 0.30329537;
	setAttr ".uvst[0].uvsp[250:406]" 0.51224577 0.30751252 0.47783631 0.30081964
		 0.47888279 0.35278141 0.49642801 0.36149603 0.463835 0.34794068 0.45814526 0.34599662
		 0.44834512 0.40553826 0.46287826 0.41789055 0.40982044 0.46729434 0.39920622 0.45131773
		 0.43543687 0.39527047 0.43061468 0.39143169 0.38762641 0.43367583 0.34079108 0.55795127
		 0.39078438 0.43844038 0.17542924 0.31663811 0.063973971 0.31838274 0.085888155 0.37124062
		 0.17134865 0.28834188 0.18121473 0.31336254 0.16485393 0.28947496 0.056773722 0.26263964
		 0.16806555 0.26474369 0.1615596 0.26412106 0.17137605 0.23855829 0.16489536 0.23645437
		 0.06523817 0.20407653 0.18406415 0.20968527 0.17860946 0.20565963 0.09227211 0.14870101
		 0.13186905 0.10318279 0.19885086 0.18354404 0.18106082 0.072784781 0.20322628 0.18883365
		 0.22557043 0.16713965 0.2402173 0.056728005 0.21321462 0.20080817 0.19615972 0.21868169
		 0.19997323 0.22148168 0.25585982 0.15968746 0.30463105 0.057767928 0.22824802 0.17325526
		 0.2342481 0.18699014 0.25675288 0.16619873 0.28655645 0.16122097 0.31288913 0.17006618
		 0.36420035 0.078820348 0.28565764 0.16782308 0.25873572 0.18084759 0.33616677 0.18580663
		 0.41045165 0.11236638 0.31032088 0.17664313 0.35334781 0.2057575 0.44228175 0.15097928
		 0.33184594 0.19104195 0.28359386 0.18275082 0.30449542 0.19139272 0.34764931 0.2102266
		 0.3648183 0.22943413 0.46394387 0.19775569 0.47452247 0.24702716 0.32225776 0.20272577
		 0.35879201 0.23218954 0.33498147 0.22013521 0.37049851 0.25776929 0.36389723 0.25816762
		 0.47175449 0.29987144 0.36821866 0.28482401 0.3616811 0.28369749 0.45814526 0.34599662
		 0.35375413 0.30655795 0.35953727 0.3097747 0.3192986 0.20625955 0.33165002 0.22278023
		 0.30292419 0.1953913 0.3169761 0.20899934 0.32915506 0.22465831 0.28286311 0.18725556
		 0.30168638 0.19836009 0.300239 0.20190382 0.31460753 0.21184617 0.30048591 0.22670919
		 0.29016525 0.2199195 0.27721569 0.21448594 0.28179958 0.19456601 0.26183951 0.21295196
		 0.28232142 0.19086605 0.26020381 0.19230461 0.23897749 0.19793874 0.24671258 0.21688533
		 0.25972611 0.18859249 0.22064081 0.20974934 0.23381008 0.22538811 0.25931016 0.1854133
		 0.23746873 0.19441658 0.23616035 0.19133484 0.21819393 0.20679271 0.21605365 0.20421296
		 0.20259155 0.22330779 0.20569682 0.2255159 0.10434461 0.58380216 0.056338727 0.62100506
		 0.098918915 0.57571566 0.064081751 0.62637407 0.028630551 0.67160571 0.037289247
		 0.67550772 0.014648438 0.73335487 0.11044165 0.59269863 0.023873931 0.73469019 0.016367309
		 0.79574513 0.072636001 0.632348 0.046677027 0.67972147 0.025931735 0.79464084 0.036236428
		 0.85626268 0.03365735 0.73608464 0.077675454 0.63590473 0.05235501 0.6822139 0.11410469
		 0.59789765 0.039660007 0.73688442 0.16333716 0.44589537 0.036265984 0.79339105 0.15246595
		 0.46583831 0.14316945 0.48241317 0.16032778 0.45137775 0.10225358 0.42857957 0.089038581
		 0.44163072 0.049894828 0.39213395 0.1138322 0.41659832 0.11820441 0.41206849 0.067113362
		 0.38238442 0.022814762 0.32870936 0.080835469 0.37424707 0.085888155 0.37124062 0.042617872
		 0.32430792 0.058134772 0.31999069 0.063973971 0.31838274 0.034319177 0.26234865 0.014648438
		 0.26112622 0.050655983 0.26255846 0.056773722 0.26263964 0.043928701 0.19833302 0.025037942
		 0.19267106 0.059490141 0.20249951 0.073344663 0.13616282 0.056793392 0.1243552 0.06523817
		 0.20407653 0.11723137 0.08656764 0.10485149 0.07193315 0.086931556 0.14526665 0.12789449
		 0.09864831 0.09227211 0.14870101 0.093622312 0.89417374 0.06016418 0.84651804 0.089550085
		 0.89855254 0.042402711 0.7925778 0.054514479 0.84889287 0.044978809 0.85276443;
	setAttr ".cuvs" -type "string" "DiffuseUV";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".clst[0].clsn" -type "string" "colorSet0";
	setAttr -s 1836 ".clst[0].clsp";
	setAttr ".clst[0].clsp[0:124]"  1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[125:249]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[250:374]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[375:499]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[500:624]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[625:749]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[750:874]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[875:999]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1000:1124]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1125:1249]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1250:1374]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1375:1499]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1500:1624]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1625:1749]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".clst[0].clsp[1750:1835]" 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
		 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1;
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr -s 407 ".vt";
	setAttr ".vt[0:165]"  31.14254379 -1.71158719 -9.88091755 32.54720306 1.42175364 -2.04946661
		 30.98532104 1.34426284 -10.17534733 32.71152115 -1.62382197 -2.20950508 32.042972565 1.46155882 5.76914692
		 32.54720306 1.42175364 -2.04946661 20.29483795 2.12951756 28.36635017 20.60113907 -1.22582793 29.35866547
		 20.81605911 1.78963792 29.79510307 -32.520401 -2.21390462 -0.49519396 -31.4014473 0.87805867 7.96173525
		 -31.4498539 -2.13924575 8.24541378 -28.038066864 0.98376131 16.2322731 -28.072061539 -2.10900235 16.52818108
		 -22.89965057 1.077485561 22.87420464 -23.066255569 -1.95901704 22.93076515 -16.068029404 -1.85822129 28.2477932
		 -16.22231483 1.15586567 27.93175125 18.88813019 -1.59753728 26.69871902 20.29483795 2.12951756 28.36635017
		 19.69360733 2.04402113 26.81316948 19.38692093 1.47418976 26.028980255 25.64212608 -1.54584193 20.19562531
		 25.98768425 1.5187242 19.57919693 29.9703083 -1.54406333 13.15547466 29.90690231 1.47859311 12.77596664
		 32.14928055 -1.57531476 5.99892235 32.042972565 1.46155882 5.76914692 16.66850853 -9.64151669 8.066277504
		 29.9703083 -1.54406333 13.15547466 31.060909271 -6.017061234 13.53340054 14.6239481 -5.73601818 7.32809162
		 13.93782902 -6.48626995 6.92283154 16.93634796 -9.82426929 8.021277428 16.66850853 -9.64151669 8.066277504
		 15.21923447 -6.51454163 3.3372817 18.1102314 -9.85114765 3.94378972 31.060909271 -6.017061234 13.53340054
		 18.30253601 -9.85733604 4.042109489 33.26781845 -6.048648834 6.24219608 32.14928055 -1.57531476 5.99892235
		 18.75242615 -9.88153267 -0.80385721 15.61255836 -6.52291775 -0.68419456 14.85195732 -6.54116726 -4.77911949
		 18.53433037 -9.87080574 -0.79496896 17.85571289 -9.8908596 -5.73753119 13.18118668 -6.6154108 -8.29224586
		 33.84806824 -6.099011421 -2.24143434 32.71152115 -1.62382197 -2.20950508 31.14254379 -1.71158719 -9.88091755
		 17.62644005 -9.91402245 -5.78250885 32.21747208 -6.19072151 -10.19548988 27.8746357 -1.78562284 -17.19966507
		 28.84101868 -6.26879406 -17.74400139 23.018619537 -1.87048173 -23.28649902 14.94415855 -10.55843163 -9.18933296
		 15.66500759 -9.86104393 -9.94056225 23.82180786 -6.35517693 -24.03338623 16.47312546 -6.45414734 -29.57608604
		 15.90877914 -1.96872783 -28.63845825 12.7155056 -9.99956799 -13.48685455 12.20872116 -10.74549961 -12.84933567
		 11.50728989 -11.6108427 -7.076913834 11.10586834 -7.029001236 -6.71970701 9.48865414 -11.66372299 -9.77003574
		 12.41948128 -10.13832855 -7.81590366 10.57304001 -7.21207619 -6.312644 13.93923473 -8.92154694 -8.88428879
		 10.4191103 -7.67642784 -6.16429806 11.2012682 -9.97253513 -11.32880116 8.5395565 -7.59392548 -8.76951218
		 8.23719978 -8.0060033798 -8.40053177 10.47869682 -10.73389912 -10.78780079 9.62750816 -11.93963146 -10.19509888
		 5.96249866 -9.1725893 -6.057342052 7.99003029 -10.13837433 -13.89210129 7.47371578 -10.90807724 -13.080223083
		 6.93981743 -13.5277462 -7.24789095 6.61662483 -11.70803833 -11.66035748 5.056553841 -13.58061218 -8.50647163
		 4.26194334 -9.22275734 -7.21278715 7.068000317 -12.10673809 -12.0018501282 2.51298642 -13.58370209 -9.63835144
		 2.1201787 -9.23137093 -8.15916252 3.48892307 -12.041091919 -13.6555109 -0.48760587 -13.60871124 -9.99922466
		 -0.42817837 -9.2616291 -8.45499992 -2.94910908 -9.26967907 -7.83858347 3.90448952 -10.010452271 -15.68908787
		 -3.47690201 -13.62923431 -9.24798965 -5.11210346 -9.30337715 -6.44818783 3.5639081 -10.89014816 -14.44366837
		 -5.87512112 -13.67243767 -7.74010944 -8.78766441 -11.98360348 -10.71253777 -7.16641426 -8.20649815 -8.94330788
		 -9.64940739 -8.12200928 -6.39831543 -5.11401701 -11.95190525 -13.33761311 -0.81001258 -11.87621117 -14.31700802
		 -0.99789214 -9.78191376 -16.18359947 -5.83660412 -9.87001896 -15.011518478 -0.89023983 -11.090629578 -14.60277843
		 -9.97470951 -10.1148777 -12.39537239 -5.24599266 -11.092370033 -13.5617981 3.18008113 -11.7603817 -12.97293377
		 -12.12889004 -11.30715942 -8.64485264 -12.81037521 -9.98607159 -9.26425552 -9.97354317 -7.63571835 -6.65435982
		 -9.098007202 -11.16638947 -11.34541607 -11.61590862 -10.19604969 -8.13783169 -10.11528683 -7.13415623 -6.78056526
		 -8.18950081 -11.83931541 -10.23470116 -10.92267418 -11.8373251 -7.39627743 -10.74050331 -7.25753021 -7.24522734
		 -4.74715376 -11.84361458 -12.34791851 -14.38982487 -10.80238247 -9.65163517 -12.70037937 -6.8136673 -8.73081589
		 -10.89658165 -10.95215416 -13.58363438 -17.67821503 -10.26856995 -5.010074615 -14.74228287 -6.83166504 -4.17667246
		 -15.0251894 -10.23338413 -10.37619209 -18.37845039 -10.20193005 -0.032650709 -15.29860973 -6.78121567 -0.036059856
		 -14.82362747 -6.80549908 3.70823574 -17.8313427 -10.19368458 4.50724602 -13.25885582 -6.70001793 7.65826416
		 -18.16726685 -10.21252918 -0.14135373 -16.16486168 -10.082698822 8.86347961 -17.48462105 -10.22818279 -5.02308321
		 -17.62854195 -10.17356682 4.35109568 -15.92361832 -9.92224693 8.86789417 -13.97859764 -5.9844265 8.050270081
		 -28.072061539 -2.10900235 16.52818108 -33.57752609 -6.70850277 -0.47203386 -29.056097031 -6.60196209 16.95821571
		 -32.47330856 -6.6319809 8.54347801 -31.4498539 -2.13924575 8.24541378 -32.520401 -2.21390462 -0.49519396
		 -31.14469147 -2.30954146 -9.67466164 -32.14077759 -6.80657101 -9.97356129 -26.85508347 -2.23480773 -18.35199928
		 -27.72309113 -6.73115635 -18.94442749 -20.49946785 -2.27109981 -25.40879822 -21.16062927 -6.76715279 -26.22076607
		 -11.42152596 -10.24618626 -14.21296787 -13.085518837 -6.72618389 -31.062381744 -12.70681381 -2.2308948 -30.08117485
		 -6.68715572 -10.23747253 -16.9984684 -3.46261263 -6.66771221 -33.51018524 -3.38981438 -2.17581916 -32.44605637
		 6.66907692 -2.075216055 -32.056610107 -6.3777914 -10.91466904 -16.29799843 -1.37221885 -10.20354271 -18.23143005
		 6.92735672 -6.56332779 -33.10482788 -1.24802756 -10.86953735 -17.4822731 4.0030250549 -10.17851734 -17.9096241
		 8.63688278 -10.077096939 -16.30544472 3.90575147 -10.86955929 -17.096256256 -0.8004114 -11.80998802 -13.24556541
		 8.35409927 -10.86084938 -15.49670506 20.81605911 1.78963792 29.79510307 28.55042076 1.83236372 22.60877991
		 20.29483795 2.12951756 28.36635017 27.61437988 2.24107623 21.47160721 19.69360733 2.04402113 26.81316948
		 33.47732925 1.80833232 14.48002243 26.52907944 2.078163624 20.2083149;
	setAttr ".vt[166:331]" 19.38692093 1.47418976 26.028980255 25.98768425 1.5187242 19.57919693
		 32.14321899 2.16272593 13.83802223 35.84765244 1.73097503 6.75165319 30.65826797 2.048291206 13.13040733
		 29.90690231 1.47859311 12.77596664 34.42742538 2.12137842 6.37679672 36.33428574 1.83574378 -1.91516685
		 32.84209061 2.026409149 5.97217989 32.042972565 1.46155882 5.76914692 34.89862823 2.10087538 -1.9743073
		 34.78525543 1.7237848 -10.84000969 33.3319397 1.96838379 -2.025587082 32.54720306 1.42175364 -2.04946661
		 33.34168243 2.014637947 -10.60208416 31.27383041 1.60757113 -18.91639328 31.76872444 1.88896585 -10.32198334
		 30.98532104 1.34426284 -10.17534733 29.90624619 1.91145539 -18.24514198 25.69094467 1.38885689 -26.020809174
		 28.4162674 1.79284012 -17.49438477 24.60368729 1.8319633 -25.028238297 17.51590538 1.43835759 -31.99399185
		 27.66967773 1.22308254 -17.10728455 16.763134 1.76378286 -30.74753189 7.28637838 1.1297884 -35.81990051
		 23.38356781 1.71268082 -23.89100266 6.97468138 1.65636027 -34.39198303 -3.8848536 1.13345003 -36.26131439
		 15.932024 1.59170818 -29.34576225 22.77563858 1.16523528 -23.31748199 27.8746357 -1.78562284 -17.19966507
		 31.14254379 -1.71158719 -9.88091755 -3.76843214 1.51270533 -34.80573273 -14.33795834 1.10067201 -33.51213074
		 6.62467575 1.52822709 -32.73545456 -13.81438065 1.47113585 -32.1425705 -22.95014191 1.037754297 -28.29175949
		 -3.62981772 1.38409781 -33.1698494 15.52049637 1.050800323 -28.63974571 -22.042953491 1.40291095 -27.10978508
		 -29.87529564 1.095245838 -20.52565575 -13.21534443 1.31139565 -30.60120964 -28.72392082 1.29937243 -19.58872604
		 6.45556641 0.93955302 -31.9008007 -3.55840516 0.85055804 -32.34482956 -21.023609161 1.26525998 -25.79222107
		 -12.91366768 0.78882647 -29.83169556 -3.38981438 -2.17581916 -32.44605637 -12.70681381 -2.2308948 -30.08117485
		 -20.51313972 0.74509215 -25.13321304 6.66907692 -2.075216055 -32.056610107 -20.49946785 -2.27109981 -25.40879822
		 15.90877914 -1.96872783 -28.63845825 23.018619537 -1.87048173 -23.28649902 23.62770844 -2.32682729 -23.91778183
		 16.29913712 -2.41192317 -29.41758537 28.6388092 -2.19979119 -17.59782028 25.34643936 -1.60622478 -25.73214912
		 6.82512569 -2.49177098 -32.91091156 17.38345909 -1.70236516 -31.64748383 -3.48285675 -2.65163016 -33.34083557
		 7.24285173 -1.74910855 -35.3527298 -13.063357353 -2.70958161 -30.84672546 -3.77531099 -1.94530368 -35.90525818
		 7.28637838 1.1297884 -35.81990051 17.51590538 1.43835759 -31.99399185 -3.8848536 1.13345003 -36.26131439
		 25.69094467 1.38885689 -26.020809174 31.27383041 1.60757113 -18.91639328 -14.11094189 -2.086853743 -33.045074463
		 -14.33795834 1.10067201 -33.51213074 30.83927917 -1.55974841 -18.74422264 34.78525543 1.7237848 -10.84000969
		 32.00040817261 -2.086838961 -10.11743736 34.47948837 -1.43769336 -10.81374168 32.54720306 1.42175364 -2.04946661
		 32.71152115 -1.62382197 -2.20950508 36.014568329 -1.29110265 -2.13018918 36.33428574 1.83574378 -1.91516685
		 33.45283508 -2.07248807 -2.11253023 32.042972565 1.46155882 5.76914692 32.14928055 -1.57531476 5.99892235
		 35.45453644 -1.2371099 6.54229307 35.84765244 1.73097503 6.75165319 33.016475677 -2.012313128 6.14554358
		 33.081886292 -1.26936936 14.18026161 33.47732925 1.80833232 14.48002243 30.78156662 -1.97482085 13.43270493
		 29.9703083 -1.54406333 13.15547466 28.30408669 -1.18866181 22.33823586 28.55042076 1.83236372 22.60877991
		 20.81605911 1.78963792 29.79510307 20.60113907 -1.22582793 29.35866547 26.33914185 -1.96027732 20.75725555
		 25.64212608 -1.54584193 20.19562531 18.88813019 -1.59753728 26.69871902 20.29483795 2.12951756 28.36635017
		 19.3410511 -1.97511744 27.39388275 -13.97859764 -5.9844265 8.050270081 -31.4498539 -2.13924575 8.24541378
		 -28.072061539 -2.10900235 16.52818108 -14.82362747 -6.80549908 3.70823574 -13.25885582 -6.70001793 7.65826416
		 -15.60287952 -6.057202339 3.8105607 -32.520401 -2.21390462 -0.49519396 -15.29860973 -6.78121567 -0.036059856
		 -16.10136986 -6.080700874 -0.14432383 -14.74228287 -6.83166504 -4.17667246 -15.53120041 -6.080700874 -4.45520401
		 -31.14469147 -2.30954146 -9.67466164 -12.70037937 -6.8136673 -8.73081589 -13.35911751 -6.07559967 -9.24615669
		 -26.85508347 -2.23480773 -18.35199928 -20.49946785 -2.27109981 -25.40879822 -10.1667738 -6.083102226 -12.65275192
		 -12.70681381 -2.2308948 -30.08117485 -9.62346363 -6.81073189 -11.98121834 -5.96227741 -6.068143845 -15.14611912
		 -3.38981438 -2.17581916 -32.44605637 -8.029130936 -7.22808743 -10.0093212128 -10.74050331 -7.25753021 -7.24522734
		 -10.11528683 -7.13415623 -6.78056526 -1.22430003 -6.040020943 -16.23564529 6.66907692 -2.075216055 -32.056610107
		 -5.63243389 -6.78087425 -14.37546825 -4.68517065 -7.23040009 -12.1147747 -1.11348259 -6.73825169 -15.41967392
		 3.56224418 -6.028338432 -15.92930222 7.63813257 -5.95261097 -14.4803257 15.90877914 -1.96872783 -28.63845825
		 3.45104122 -6.73187733 -15.093065262 -0.82385975 -7.19519138 -13.03808403 11.21927929 -5.90013218 -11.97163963
		 23.018619537 -1.87048173 -23.28649902 7.34427071 -6.73450089 -13.68192101 13.82825661 -5.77276802 -8.8215065
		 27.8746357 -1.78562284 -17.19966507 10.69991207 -6.65217781 -11.3300724 3.078931808 -7.15305805 -12.65312004
		 6.36359119 -7.10951614 -11.30047989 13.18118668 -6.6154108 -8.29224586 15.58559227 -5.82118702 -5.13167191
		 31.14254379 -1.71158719 -9.88091755 32.71152115 -1.62382197 -2.20950508 9.091702461 -7.073091507 -9.44067192
		 14.85195732 -6.54116726 -4.77911949 11.10586834 -7.029001236 -6.71970701 16.39981461 -5.77465153 -0.72213459
		 15.61255836 -6.52291775 -0.68419456 32.14928055 -1.57531476 5.99892235 16.0020427704 -5.76808357 3.47042942
		 15.21923447 -6.51454163 3.3372817 29.9703083 -1.54406333 13.15547466 13.93782902 -6.48626995 6.92283154
		 14.6239481 -5.73601818 7.32809162 8.58054829 -6.99073792 -8.85758781 10.57304001 -7.21207619 -6.312644
		 6.095806122 -7.22343159 -10.65850925 8.5395565 -7.59392548 -8.76951218 10.4191103 -7.67642784 -6.16429806
		 2.94743299 -7.08326149 -11.90053749 6.052753925 -7.71424675 -10.47003937 5.87909269 -8.10946846 -10.014821053
		 8.23719978 -8.0060033798 -8.40053177 5.96249866 -9.1725893 -6.057342052;
	setAttr ".vt[332:406]" 4.26194334 -9.22275734 -7.21278715 2.1201787 -9.23137093 -8.15916252
		 2.89682031 -8.097444534 -11.32377338 -0.42817837 -9.2616291 -8.45499992 2.96311808 -7.69358063 -11.80503464
		 -0.64711511 -8.065096855 -11.71147346 -4.15680456 -8.16009712 -10.87877655 -2.94910908 -9.26967907 -7.83858347
		 -0.7064302 -7.60277653 -12.12079811 -7.16641426 -8.20649815 -8.94330788 -5.11210346 -9.30337715 -6.44818783
		 -0.74238104 -7.097567558 -12.28468895 -4.3178792 -7.65619087 -11.25221252 -4.38100481 -7.10850906 -11.3891058
		 -7.46024799 -7.77525234 -9.30610275 -7.56698799 -7.24774551 -9.43749809 -9.97354317 -7.63571835 -6.65435982
		 -9.64940739 -8.12200928 -6.39831543 -17.32061386 1.90666699 30.23502541 -25.70728111 1.34488535 25.57201576
		 -17.93087578 1.43570399 31.57783318 -24.68091393 1.80513012 24.58287239 -31.31423187 1.30033612 18.37970352
		 -30.092540741 1.65879166 17.56826401 -35.062084198 1.2668314 9.09297657 -16.59018517 1.70888567 28.6944313
		 -33.6643486 1.49243927 8.65444851 -36.33428574 1.099234104 -0.69611311 -23.49246025 1.6162138 23.43957329
		 -28.72580147 1.53197765 16.67663765 -34.84676743 1.45485783 -0.76490307 -34.73566818 1.07240057 -10.64257622
		 -32.16462708 1.41666842 8.1914053 -22.89965057 1.077485561 22.87420464 -28.038066864 0.98376131 16.2322731
		 -16.22231483 1.15586567 27.93175125 -31.4014473 0.87805867 7.96173525 -16.068029404 -1.85822129 28.2477932
		 -33.19649887 1.33775449 -0.82847595 -17.71864128 -1.57151914 31.24378014 -17.93087578 1.43570399 31.57783318
		 -16.49616432 -2.30641341 29.033123016 -25.45409966 -1.59995341 25.39341736 -25.70728111 1.34488535 25.57201576
		 -31.31423187 1.30033612 18.37970352 -23.68709946 -2.4104259 23.58072472 -23.066255569 -1.95901704 22.93076515
		 -30.91442871 -1.82108426 18.21048927 -35.062084198 1.2668314 9.09297657 -28.80237389 -2.49937606 16.96719551
		 -28.072061539 -2.10900235 16.52818108 -34.68465424 -1.94570422 9.14244556 -32.28086853 -2.57803845 8.47892094
		 -31.4498539 -2.13924575 8.24541378 -35.9197464 -2.011853456 -0.54313707 -36.33428574 1.099234104 -0.69611311
		 -33.39319611 -2.65334964 -0.50400925 -32.520401 -2.21390462 -0.49519396 -34.35964584 -2.046144247 -10.55373764
		 -34.73566818 1.07240057 -10.64257622 -31.96969414 -2.72532535 -9.90029335 -29.66648293 -2.14057994 -20.26440811
		 -29.87529564 1.095245838 -20.52565575 -31.14469147 -2.30954146 -9.67466164 -22.6589489 -2.03800559 -27.94228172
		 -22.95014191 1.037754297 -28.29175949 -27.57220268 -2.78429961 -18.82468605 -21.050991058 -2.70892882 -26.06070137
		 -26.85508347 -2.23480773 -18.35199928 -26.87113953 0.73699784 -18.096252441 -30.94239044 0.753335 -9.77693748
		 -27.49650764 1.24232554 -18.5990448 -32.3683548 0.80796552 -0.85555792 -31.73372269 1.2910409 -9.96116638
		 -33.3216362 1.45094419 -10.32946873;
	setAttr -s 1013 ".ed";
	setAttr ".ed[0:165]"  0 1 0 1 2 0 2 0 0 3 4 0 4 5 0 5 3 0 6 7 0 7 8 0 8 6 0
		 9 10 0 10 11 1 11 9 0 12 11 1 10 12 0 12 13 1 13 11 0 14 13 1 12 14 0 14 15 1 15 13 0
		 16 15 0 14 16 1 14 17 0 17 16 0 18 19 0 19 20 0 20 18 1 20 21 0 21 18 1 22 18 0 21 22 1
		 21 23 0 23 22 1 24 22 0 23 24 1 23 25 0 25 24 1 26 24 0 25 26 1 25 27 0 27 26 0 28 29 1
		 29 30 0 30 28 0 28 31 0 31 29 0 31 32 0 32 33 1 33 31 1 33 34 1 34 31 0 35 33 1 32 35 0
		 33 36 1 36 34 1 36 37 1 37 34 0 35 38 1 38 33 1 38 36 1 39 29 1 29 37 0 37 39 1 36 39 1
		 39 40 1 40 29 0 41 38 1 35 41 1 41 36 1 35 42 0 42 41 1 43 41 1 42 43 0 44 39 1 36 44 1
		 41 44 1 43 45 1 45 41 1 45 44 1 46 45 1 43 46 0 44 47 1 47 39 1 47 40 1 47 48 1 48 40 0
		 47 49 1 49 48 0 50 44 1 45 50 1 50 47 1 47 51 1 51 49 1 50 51 1 51 52 1 52 49 0 51 53 1
		 53 52 1 50 53 1 53 54 1 54 52 0 45 55 1 55 50 1 46 55 1 50 56 1 56 53 1 55 56 1 53 57 1
		 57 54 1 56 57 1 58 54 1 57 58 1 58 59 1 59 54 0 56 60 1 60 57 1 60 58 1 61 56 1 55 61 1
		 61 60 1 46 62 1 62 55 1 46 63 0 63 62 1 64 55 1 62 64 1 64 61 1 65 62 1 63 65 1 65 64 1
		 63 66 0 66 65 1 67 65 1 66 67 1 66 68 0 68 67 1 68 69 1 69 67 1 69 65 1 68 70 0 70 69 1
		 71 69 1 70 71 0 65 72 1 72 64 1 69 72 1 71 73 1 73 69 1 74 73 1 71 74 0 69 75 1 75 72 1
		 73 75 1 72 76 1 76 64 1 75 76 1 74 77 1 77 73 1 76 78 1 78 64 1 78 61 1 74 79 1 79 77 1
		 74 80 0 80 79 1 77 81 1;
	setAttr ".ed[166:331]" 81 73 1 79 81 1 81 75 1 80 82 1 82 79 1 82 81 1 80 83 0
		 83 82 1 84 75 1 81 84 1 82 84 1 85 82 1 83 85 1 85 84 1 83 86 0 86 85 1 87 85 1 86 87 0
		 84 88 1 88 75 1 88 76 1 87 89 1 89 85 1 90 89 1 87 90 0 88 91 1 91 76 1 91 78 1 90 92 1
		 92 89 1 90 93 1 93 92 1 93 89 1 90 94 0 94 93 1 95 93 1 94 95 0 89 96 1 96 85 1 93 96 1
		 96 97 1 97 85 1 97 84 1 98 84 1 97 98 1 96 98 1 98 88 1 98 91 1 96 99 1 99 98 1 100 91 1
		 98 100 1 99 100 1 96 101 1 101 99 1 93 101 1 102 100 1 99 102 1 101 102 1 100 103 1
		 103 91 1 103 78 1 93 104 1 104 101 1 95 104 1 95 105 1 105 104 1 105 101 1 106 105 1
		 95 106 0 105 107 1 107 101 1 107 102 1 108 105 1 106 108 1 108 107 1 106 109 0 109 108 1
		 108 110 1 110 107 1 110 102 1 111 108 1 109 111 1 111 110 1 109 112 0 112 111 1 110 113 1
		 113 102 1 114 111 1 112 114 1 112 115 0 115 114 1 111 116 1 116 110 1 114 116 1 116 113 1
		 117 114 1 115 117 1 115 118 0 118 117 1 119 116 1 114 119 1 117 119 1 120 117 1 118 120 1
		 118 121 0 121 120 1 122 120 1 121 122 0 122 123 1 123 120 1 124 123 1 122 124 0 125 117 1
		 120 125 1 124 126 1 126 123 1 125 127 1 127 117 1 127 119 1 128 120 1 123 128 1 128 125 1
		 126 128 1 129 126 1 124 129 1 129 128 1 124 130 0 130 129 1 131 129 1 130 131 0 128 132 1
		 132 125 1 132 127 1 131 133 1 133 129 1 129 134 1 134 128 1 133 134 1 131 134 1 134 132 1
		 131 135 0 135 134 1 135 132 1 135 136 0 136 132 1 137 132 1 136 137 0 137 138 1 138 132 1
		 138 127 1 139 138 1 137 139 0 138 119 1 139 140 1 140 138 1 140 119 1 141 140 1 139 141 0
		 142 119 1 140 142 1 141 142 1 142 143 1 143 119 1 143 116 1 144 142 1;
	setAttr ".ed[332:497]" 141 144 1 144 143 1 141 145 0 145 144 1 146 116 1 143 146 1
		 144 146 1 147 144 1 145 147 1 147 146 1 145 148 0 148 147 1 149 147 1 148 149 0 150 116 1
		 146 150 1 150 113 1 147 151 1 151 146 1 151 150 1 149 152 1 152 147 1 152 151 1 59 152 1
		 149 59 0 58 152 1 153 150 1 151 153 1 153 113 1 152 154 1 154 151 1 154 153 1 58 155 1
		 155 152 1 155 154 1 60 155 1 156 153 1 154 156 1 155 156 1 157 113 1 153 157 1 156 157 1
		 157 102 1 157 100 1 157 103 1 156 103 1 155 158 1 158 156 1 158 103 1 60 158 1 158 78 1
		 61 158 1 159 160 0 160 161 1 161 159 0 160 162 1 162 161 1 162 163 1 163 161 0 164 162 1
		 160 164 0 165 163 1 162 165 1 165 166 1 166 163 0 167 166 0 165 167 1 164 168 1 168 162 1
		 168 165 1 169 168 1 164 169 0 165 170 1 170 167 1 168 170 1 171 167 0 170 171 1 172 168 1
		 169 172 1 172 170 1 173 172 1 169 173 0 170 174 1 174 171 1 172 174 1 175 171 0 174 175 1
		 176 172 1 173 176 1 176 174 1 173 177 0 177 176 1 178 175 1 174 178 1 176 178 1 179 175 0
		 178 179 1 180 176 1 177 180 1 180 178 1 177 181 0 181 180 1 182 179 1 178 182 1 180 182 1
		 182 183 1 183 179 0 184 180 1 181 184 1 184 182 1 181 185 0 185 184 1 184 186 1 186 182 1
		 186 183 1 185 187 1 187 184 1 187 186 1 185 188 0 188 187 1 186 189 1 189 183 1 188 190 1
		 190 187 1 188 191 0 191 190 1 187 192 1 192 186 1 190 192 1 192 189 1 191 193 1 193 190 1
		 194 193 1 191 194 0 190 195 1 195 192 1 193 195 1 192 196 1 196 189 1 195 196 1 197 183 1
		 189 197 1 196 197 1 197 198 1 198 183 0 194 199 1 199 193 1 200 199 1 194 200 0 201 195 1
		 193 201 1 199 201 1 202 199 1 200 202 1 203 202 1 200 203 0 204 201 1 199 204 1 202 204 1
		 201 205 1 205 195 1 205 196 1 206 202 1 203 206 1 203 207 0 207 206 1;
	setAttr ".ed[498:663]" 206 208 1 208 202 1 208 204 1 209 206 1 207 209 1 204 210 1
		 210 201 1 210 205 1 208 211 1 211 204 1 211 210 1 206 212 1 212 208 1 209 212 1 213 211 1
		 208 213 1 212 213 1 214 210 1 211 214 1 215 211 1 213 215 1 215 214 1 212 216 1 216 213 1
		 214 217 1 217 210 1 217 205 1 213 218 1 218 215 1 216 218 1 217 219 1 219 205 1 219 196 1
		 219 220 1 220 196 1 220 197 1 219 221 1 221 220 1 221 197 1 217 222 1 222 219 1 222 221 1
		 221 223 1 223 197 1 223 198 1 222 224 1 224 221 1 224 223 1 225 222 1 217 225 1 214 225 1
		 226 224 1 222 226 1 225 226 1 214 227 1 227 225 1 215 227 1 228 226 1 225 228 1 227 228 1
		 215 229 1 229 227 1 218 229 1 230 228 1 227 230 1 229 230 1 231 226 1 228 231 1 230 231 1
		 231 232 0 232 226 1 232 224 1 233 231 0 230 233 1 232 234 0 234 224 1 235 224 1 234 235 0
		 236 233 1 230 236 1 229 236 1 236 237 1 237 233 0 235 238 1 238 224 1 238 223 1 239 238 1
		 235 239 0 238 240 1 240 223 1 240 198 1 239 241 1 241 238 1 241 240 1 242 198 0 198 243 1
		 243 242 0 240 243 1 239 244 1 244 241 1 239 245 0 245 244 1 241 246 1 246 240 1 246 243 1
		 244 246 1 247 243 0 243 248 1 248 247 0 246 248 1 245 249 1 249 244 1 245 250 0 250 249 1
		 244 251 1 251 246 1 249 251 1 251 248 1 250 252 1 252 249 1 252 251 1 250 253 0 253 252 1
		 254 248 1 251 254 1 252 254 1 254 255 1 255 248 0 253 256 1 256 252 1 256 254 1 253 257 0
		 257 256 1 257 258 0 258 256 1 259 256 1 258 259 0 260 255 1 254 260 1 256 260 1 260 261 1
		 261 255 0 260 262 1 262 261 0 262 259 1 259 263 0 263 262 0 256 264 1 264 260 1 264 262 1
		 259 264 1 265 266 1 266 267 0 267 265 0 268 265 1 265 269 0 269 268 0 265 270 1 270 266 1
		 268 270 1 270 271 1 271 266 0 272 270 1 268 272 0 272 273 1 273 270 1;
	setAttr ".ed[664:829]" 273 271 1 274 273 1 272 274 0 275 271 1 273 275 1 274 275 1
		 275 276 1 276 271 0 277 275 1 274 277 0 278 276 1 275 278 1 277 278 1 278 279 1 279 276 0
		 278 280 1 280 279 0 278 281 1 281 280 1 281 282 1 282 280 0 283 278 1 277 283 1 283 281 1
		 281 284 1 284 282 1 283 284 1 284 285 1 285 282 0 277 286 1 286 283 1 277 287 0 287 286 1
		 287 288 0 288 286 1 284 289 1 289 285 1 289 290 1 290 285 0 283 291 1 291 284 1 291 289 1
		 283 292 1 292 291 1 286 292 1 291 293 1 293 289 1 292 293 1 289 294 1 294 290 1 293 294 1
		 295 290 1 294 295 1 295 296 1 296 290 0 293 297 1 297 294 1 297 295 1 292 298 1 298 293 1
		 298 297 1 299 296 1 295 299 1 299 300 1 300 296 0 297 301 1 301 295 1 301 299 1 299 302 1
		 302 300 1 302 303 1 303 300 0 301 304 1 304 299 1 304 302 1 297 305 1 305 301 1 298 305 1
		 306 304 1 301 306 1 305 306 1 304 307 1 307 302 1 308 303 1 302 308 1 307 308 1 308 309 1
		 309 303 0 308 310 1 310 309 0 311 307 1 304 311 1 306 311 1 307 312 0 312 308 1 311 313 1
		 313 307 0 314 308 1 312 314 1 314 310 1 312 315 0 315 314 1 314 316 1 316 310 0 317 314 1
		 315 317 1 317 316 1 315 318 0 318 317 1 317 319 1 319 316 0 320 317 1 318 320 0 317 321 1
		 321 319 0 320 321 0 322 313 1 311 322 1 322 323 1 323 313 0 311 324 1 324 322 1 306 324 1
		 325 323 1 322 325 1 324 325 1 325 326 0 326 323 0 306 327 1 327 324 1 305 327 1 324 328 1
		 328 325 1 327 328 1 328 329 1 329 325 1 329 330 1 330 325 0 329 331 1 331 330 0 329 332 1
		 332 331 0 329 333 1 333 332 0 329 334 1 334 333 1 328 334 1 334 335 1 335 333 0 328 336 1
		 336 334 1 327 336 1 334 337 1 337 335 1 336 337 1 338 335 1 337 338 1 338 339 1 339 335 0
		 336 340 1 340 337 1 327 340 1 340 338 1 341 342 0 342 339 0 339 341 1;
	setAttr ".ed[830:995]" 338 341 1 327 343 1 343 340 1 305 343 1 298 343 1 340 344 1
		 344 338 1 343 344 1 298 345 1 345 343 1 345 344 1 292 345 1 286 345 1 346 338 1 344 346 1
		 345 346 1 346 341 1 286 347 1 347 345 1 347 346 1 288 347 1 288 346 1 288 348 0 348 346 1
		 348 341 1 348 349 0 349 341 0 350 351 1 351 352 0 352 350 0 350 353 1 353 351 1 353 354 1
		 354 351 0 353 355 1 355 354 1 355 356 1 356 354 0 357 353 1 350 357 1 355 358 1 358 356 1
		 358 359 1 359 356 0 360 355 1 353 360 1 357 360 1 361 358 1 355 361 1 360 361 1 358 362 1
		 362 359 1 362 363 1 363 359 0 361 364 1 364 358 1 364 362 1 365 361 1 360 365 1 365 366 0
		 366 361 1 366 364 1 360 367 1 367 365 0 357 367 1 366 368 0 368 364 1 357 369 1 369 367 0
		 368 370 1 370 364 1 370 362 1 357 371 1 371 369 1 350 371 1 350 372 0 372 371 1 371 373 1
		 373 369 1 372 374 1 374 371 1 374 373 1 372 375 0 375 374 1 376 374 1 375 376 0 377 369 1
		 373 377 1 374 377 1 377 378 1 378 369 0 376 379 1 379 374 1 379 377 1 380 379 1 376 380 0
		 381 378 1 377 381 1 379 381 1 381 382 1 382 378 0 380 383 1 383 379 1 383 381 1 381 384 1
		 384 382 1 383 384 1 384 385 1 385 382 0 380 386 1 386 383 1 386 384 1 380 387 0 387 386 1
		 384 388 1 388 385 1 386 388 1 388 389 1 389 385 0 387 390 1 390 386 1 390 388 1 387 391 0
		 391 390 1 390 392 1 392 388 1 392 389 1 391 393 1 393 390 1 393 392 1 391 394 0 394 393 1
		 395 389 1 392 395 1 394 396 1 396 393 1 394 397 0 397 396 1 237 396 1 397 237 0 236 396 1
		 393 398 1 398 392 1 396 398 1 398 395 1 236 399 1 399 396 1 399 398 1 229 399 1 218 399 1
		 399 400 1 400 398 1 218 400 1 400 395 1 216 400 1 401 395 1 400 401 1 216 401 1 401 402 1
		 402 395 1 216 403 1 403 401 1 403 402 1 212 403 1 209 403 1 404 395 1;
	setAttr ".ed[996:1012]" 402 404 1 404 389 1 368 389 0 404 368 1 404 370 1 403 405 1
		 405 402 1 405 404 1 209 405 1 405 370 1 209 406 1 406 405 1 406 370 1 207 406 1 406 362 1
		 207 363 0 363 406 1;
	setAttr -s 409 ".n";
	setAttr ".n[0:165]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[166:331]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr ".n[332:408]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20;
	setAttr -s 612 -ch 1836 ".fc";
	setAttr ".fc[0:499]" -type "polyFaces" 
		f 3 0 1 2
		mu 0 3 0 1 2
		mc 0 3 0 1 2
		f 3 3 4 5
		mu 0 3 3 4 5
		mc 0 3 3 4 5
		f 3 6 7 8
		mu 0 3 6 7 8
		mc 0 3 6 7 8
		f 3 9 10 11
		mu 0 3 9 10 11
		mc 0 3 9 10 12
		f 3 12 -11 13
		mu 0 3 12 11 10
		mc 0 3 15 13 11
		f 3 -13 14 15
		mu 0 3 11 12 13
		mc 0 3 14 16 18
		f 3 16 -15 17
		mu 0 3 14 13 12
		mc 0 3 21 19 17
		f 3 -17 18 19
		mu 0 3 13 14 15
		mc 0 3 20 22 25
		f 3 20 -19 21
		mu 0 3 16 15 14
		mc 0 3 27 26 23
		f 3 -22 22 23
		mu 0 3 16 14 17
		mc 0 3 28 24 29
		f 3 24 25 26
		mu 0 3 18 19 20
		mc 0 3 30 33 34
		f 3 -27 27 28
		mu 0 3 18 20 21
		mc 0 3 31 35 36
		f 3 29 -29 30
		mu 0 3 22 18 21
		mc 0 3 39 32 37
		f 3 -31 31 32
		mu 0 3 22 21 23
		mc 0 3 40 38 42
		f 3 33 -33 34
		mu 0 3 24 22 23
		mc 0 3 45 41 43
		f 3 -35 35 36
		mu 0 3 24 23 25
		mc 0 3 46 44 48
		f 3 37 -37 38
		mu 0 3 26 24 25
		mc 0 3 51 47 49
		f 3 -39 39 40
		mu 0 3 26 25 27
		mc 0 3 52 50 53
		f 3 41 42 43
		mu 0 3 28 29 30
		mc 0 3 54 56 60
		f 3 -42 44 45
		mu 0 3 29 28 31
		mc 0 3 57 55 61
		f 3 46 47 48
		mu 0 3 31 32 33
		mc 0 3 62 64 66
		f 3 49 50 -49
		mu 0 3 33 34 31
		mc 0 3 67 72 63
		f 3 51 -48 52
		mu 0 3 35 33 32
		mc 0 3 75 68 65
		f 3 53 54 -50
		mu 0 3 33 36 34
		mc 0 3 69 79 73
		f 3 55 56 -55
		mu 0 3 36 37 34
		mc 0 3 80 86 74
		f 3 -52 57 58
		mu 0 3 33 35 38
		mc 0 3 70 76 89
		f 3 -54 -59 59
		mu 0 3 36 33 38
		mc 0 3 81 71 90
		f 3 60 61 62
		mu 0 3 39 29 37
		mc 0 3 93 58 87
		f 3 -56 63 -63
		mu 0 3 37 36 39
		mc 0 3 88 82 94
		f 3 -61 64 65
		mu 0 3 29 39 40
		mc 0 3 59 95 99
		f 3 66 -58 67
		mu 0 3 41 38 35
		mc 0 3 102 91 77
		f 3 -67 68 -60
		mu 0 3 38 41 36
		mc 0 3 92 103 83
		f 3 -68 69 70
		mu 0 3 41 35 42
		mc 0 3 104 78 109
		f 3 71 -71 72
		mu 0 3 43 41 42
		mc 0 3 111 105 110
		f 3 73 -64 74
		mu 0 3 44 39 36
		mc 0 3 114 96 84
		f 3 -69 75 -75
		mu 0 3 36 41 44
		mc 0 3 85 106 115
		f 3 -72 76 77
		mu 0 3 41 43 45
		mc 0 3 107 112 120
		f 3 78 -76 -78
		mu 0 3 45 44 41
		mc 0 3 121 116 108
		f 3 79 -77 80
		mu 0 3 46 45 43
		mc 0 3 126 122 113
		f 3 -74 81 82
		mu 0 3 39 44 47
		mc 0 3 97 117 130
		f 3 83 -65 -83
		mu 0 3 47 40 39
		mc 0 3 131 100 98
		f 3 -84 84 85
		mu 0 3 40 47 48
		mc 0 3 101 132 137
		f 3 86 87 -85
		mu 0 3 47 49 48
		mc 0 3 133 139 138
		f 3 88 -79 89
		mu 0 3 50 44 45
		mc 0 3 142 118 123
		f 3 90 -82 -89
		mu 0 3 50 47 44
		mc 0 3 143 134 119
		f 3 91 92 -87
		mu 0 3 47 51 49
		mc 0 3 135 149 140
		f 3 -91 93 -92
		mu 0 3 47 50 51
		mc 0 3 136 144 150
		f 3 94 95 -93
		mu 0 3 51 52 49
		mc 0 3 151 154 141
		f 3 96 97 -95
		mu 0 3 51 53 52
		mc 0 3 152 157 155
		f 3 98 -97 -94
		mu 0 3 50 53 51
		mc 0 3 145 158 153
		f 3 99 100 -98
		mu 0 3 53 54 52
		mc 0 3 159 163 156
		f 3 -90 101 102
		mu 0 3 50 45 55
		mc 0 3 146 124 167
		f 3 -80 103 -102
		mu 0 3 45 46 55
		mc 0 3 125 127 168
		f 3 -99 104 105
		mu 0 3 53 50 56
		mc 0 3 160 147 174
		f 3 106 -105 -103
		mu 0 3 55 56 50
		mc 0 3 169 175 148
		f 3 107 108 -100
		mu 0 3 53 57 54
		mc 0 3 161 180 164
		f 3 -106 109 -108
		mu 0 3 53 56 57
		mc 0 3 162 176 181
		f 3 110 -109 111
		mu 0 3 58 54 57
		mc 0 3 185 165 182
		f 3 -111 112 113
		mu 0 3 54 58 59
		mc 0 3 166 186 191
		f 3 -110 114 115
		mu 0 3 57 56 60
		mc 0 3 183 177 194
		f 3 116 -112 -116
		mu 0 3 60 58 57
		mc 0 3 195 187 184
		f 3 117 -107 118
		mu 0 3 61 56 55
		mc 0 3 200 178 170
		f 3 -118 119 -115
		mu 0 3 56 61 60
		mc 0 3 179 201 196
		f 3 -104 120 121
		mu 0 3 55 46 62
		mc 0 3 171 128 206
		f 3 -121 122 123
		mu 0 3 62 46 63
		mc 0 3 207 129 211
		f 3 124 -122 125
		mu 0 3 64 55 62
		mc 0 3 214 172 208
		f 3 -125 126 -119
		mu 0 3 55 64 61
		mc 0 3 173 215 202
		f 3 127 -124 128
		mu 0 3 65 62 63
		mc 0 3 221 209 212
		f 3 129 -126 -128
		mu 0 3 65 64 62
		mc 0 3 222 216 210
		f 3 130 131 -129
		mu 0 3 63 66 65
		mc 0 3 213 228 223
		f 3 132 -132 133
		mu 0 3 67 65 66
		mc 0 3 231 224 229
		f 3 134 135 -134
		mu 0 3 66 68 67
		mc 0 3 230 235 232
		f 3 136 137 -136
		mu 0 3 68 69 67
		mc 0 3 236 238 233
		f 3 138 -133 -138
		mu 0 3 69 65 67
		mc 0 3 239 225 234
		f 3 -137 139 140
		mu 0 3 69 68 70
		mc 0 3 240 237 246
		f 3 141 -141 142
		mu 0 3 71 69 70
		mc 0 3 248 241 247
		f 3 -130 143 144
		mu 0 3 64 65 72
		mc 0 3 217 226 251
		f 3 -139 145 -144
		mu 0 3 65 69 72
		mc 0 3 227 242 252
		f 3 -142 146 147
		mu 0 3 69 71 73
		mc 0 3 243 249 256
		f 3 148 -147 149
		mu 0 3 74 73 71
		mc 0 3 262 257 250
		f 3 150 151 -146
		mu 0 3 69 75 72
		mc 0 3 244 266 253
		f 3 152 -151 -148
		mu 0 3 73 75 69
		mc 0 3 258 267 245
		f 3 153 154 -145
		mu 0 3 72 76 64
		mc 0 3 254 273 218
		f 3 -152 155 -154
		mu 0 3 72 75 76
		mc 0 3 255 268 274
		f 3 -149 156 157
		mu 0 3 73 74 77
		mc 0 3 259 263 279
		f 3 -155 158 159
		mu 0 3 64 76 78
		mc 0 3 219 275 283
		f 3 160 -127 -160
		mu 0 3 78 61 64
		mc 0 3 284 203 220
		f 3 -157 161 162
		mu 0 3 77 74 79
		mc 0 3 280 264 289
		f 3 163 164 -162
		mu 0 3 74 80 79
		mc 0 3 265 294 290
		f 3 165 166 -158
		mu 0 3 77 81 73
		mc 0 3 281 297 260
		f 3 -166 -163 167
		mu 0 3 81 77 79
		mc 0 3 298 282 291
		f 3 -153 -167 168
		mu 0 3 75 73 81
		mc 0 3 269 261 299
		f 3 -165 169 170
		mu 0 3 79 80 82
		mc 0 3 292 295 303
		f 3 171 -168 -171
		mu 0 3 82 81 79
		mc 0 3 304 300 293
		f 3 -170 172 173
		mu 0 3 82 80 83
		mc 0 3 305 296 309
		f 3 174 -169 175
		mu 0 3 84 75 81
		mc 0 3 312 270 301
		f 3 -172 176 -176
		mu 0 3 81 82 84
		mc 0 3 302 306 313
		f 3 177 -174 178
		mu 0 3 85 82 83
		mc 0 3 319 307 310
		f 3 179 -177 -178
		mu 0 3 85 84 82
		mc 0 3 320 314 308
		f 3 -179 180 181
		mu 0 3 85 83 86
		mc 0 3 321 311 327
		f 3 182 -182 183
		mu 0 3 87 85 86
		mc 0 3 329 322 328
		f 3 -175 184 185
		mu 0 3 75 84 88
		mc 0 3 271 315 332
		f 3 -186 186 -156
		mu 0 3 75 88 76
		mc 0 3 272 333 276
		f 3 -183 187 188
		mu 0 3 85 87 89
		mc 0 3 323 330 337
		f 3 189 -188 190
		mu 0 3 90 89 87
		mc 0 3 343 338 331
		f 3 191 192 -187
		mu 0 3 88 91 76
		mc 0 3 334 347 277
		f 3 -193 193 -159
		mu 0 3 76 91 78
		mc 0 3 278 348 285
		f 3 -190 194 195
		mu 0 3 89 90 92
		mc 0 3 339 344 353
		f 3 196 197 -195
		mu 0 3 90 93 92
		mc 0 3 345 356 354
		f 3 -196 -198 198
		mu 0 3 89 92 93
		mc 0 3 340 355 357
		f 3 -197 199 200
		mu 0 3 93 90 94
		mc 0 3 358 346 364
		f 3 201 -201 202
		mu 0 3 95 93 94
		mc 0 3 366 359 365
		f 3 203 204 -189
		mu 0 3 89 96 85
		mc 0 3 341 370 324
		f 3 -204 -199 205
		mu 0 3 96 89 93
		mc 0 3 371 342 360
		f 3 -205 206 207
		mu 0 3 85 96 97
		mc 0 3 325 372 377
		f 3 -180 -208 208
		mu 0 3 84 85 97
		mc 0 3 316 326 378
		f 3 209 -209 210
		mu 0 3 98 84 97
		mc 0 3 381 317 379
		f 3 211 -211 -207
		mu 0 3 96 98 97
		mc 0 3 373 382 380
		f 3 -210 212 -185
		mu 0 3 84 98 88
		mc 0 3 318 383 335
		f 3 -213 213 -192
		mu 0 3 88 98 91
		mc 0 3 336 384 349
		f 3 -212 214 215
		mu 0 3 98 96 99
		mc 0 3 385 374 388
		f 3 216 -214 217
		mu 0 3 100 91 98
		mc 0 3 393 350 386
		f 3 -216 218 -218
		mu 0 3 98 99 100
		mc 0 3 387 389 394
		f 3 219 220 -215
		mu 0 3 96 101 99
		mc 0 3 375 399 390
		f 3 -220 -206 221
		mu 0 3 101 96 93
		mc 0 3 400 376 361
		f 3 222 -219 223
		mu 0 3 102 100 99
		mc 0 3 406 395 391
		f 3 224 -224 -221
		mu 0 3 101 102 99
		mc 0 3 401 407 392
		f 3 -217 225 226
		mu 0 3 91 100 103
		mc 0 3 351 396 413
		f 3 -227 227 -194
		mu 0 3 91 103 78
		mc 0 3 352 414 286
		f 3 228 229 -222
		mu 0 3 93 104 101
		mc 0 3 362 419 402
		f 3 -202 230 -229
		mu 0 3 93 95 104
		mc 0 3 363 367 420
		f 3 231 232 -231
		mu 0 3 95 105 104
		mc 0 3 368 423 421
		f 3 -230 -233 233
		mu 0 3 101 104 105
		mc 0 3 403 422 424
		f 3 234 -232 235
		mu 0 3 106 105 95
		mc 0 3 429 425 369
		f 3 236 237 -234
		mu 0 3 105 107 101
		mc 0 3 426 432 404
		f 3 -225 -238 238
		mu 0 3 102 101 107
		mc 0 3 408 405 433
		f 3 239 -235 240
		mu 0 3 108 105 106
		mc 0 3 437 427 430
		f 3 -237 -240 241
		mu 0 3 107 105 108
		mc 0 3 434 428 438
		f 3 242 243 -241
		mu 0 3 106 109 108
		mc 0 3 431 443 439
		f 3 244 245 -242
		mu 0 3 108 110 107
		mc 0 3 440 446 435
		f 3 246 -239 -246
		mu 0 3 110 102 107
		mc 0 3 447 409 436
		f 3 247 -244 248
		mu 0 3 111 108 109
		mc 0 3 452 441 444
		f 3 -245 -248 249
		mu 0 3 110 108 111
		mc 0 3 448 442 453
		f 3 250 251 -249
		mu 0 3 109 112 111
		mc 0 3 445 458 454
		f 3 -247 252 253
		mu 0 3 102 110 113
		mc 0 3 410 449 461
		f 3 254 -252 255
		mu 0 3 114 111 112
		mc 0 3 467 455 459
		f 3 -256 256 257
		mu 0 3 114 112 115
		mc 0 3 468 460 473
		f 3 258 259 -250
		mu 0 3 111 116 110
		mc 0 3 456 476 450
		f 3 -259 -255 260
		mu 0 3 116 111 114
		mc 0 3 477 457 469
		f 3 261 -253 -260
		mu 0 3 116 113 110
		mc 0 3 478 462 451
		f 3 262 -258 263
		mu 0 3 117 114 115
		mc 0 3 484 470 474
		f 3 264 265 -264
		mu 0 3 115 118 117
		mc 0 3 475 491 485
		f 3 266 -261 267
		mu 0 3 119 116 114
		mc 0 3 494 479 471
		f 3 -268 -263 268
		mu 0 3 119 114 117
		mc 0 3 495 472 486
		f 3 269 -266 270
		mu 0 3 120 117 118
		mc 0 3 502 487 492
		f 3 -271 271 272
		mu 0 3 120 118 121
		mc 0 3 503 493 509
		f 3 273 -273 274
		mu 0 3 122 120 121
		mc 0 3 511 504 510
		f 3 -274 275 276
		mu 0 3 120 122 123
		mc 0 3 505 512 514
		f 3 277 -276 278
		mu 0 3 124 123 122
		mc 0 3 519 515 513
		f 3 279 -270 280
		mu 0 3 125 117 120
		mc 0 3 523 488 506
		f 3 -278 281 282
		mu 0 3 123 124 126
		mc 0 3 516 520 528
		f 3 -280 283 284
		mu 0 3 117 125 127
		mc 0 3 489 524 532
		f 3 -285 285 -269
		mu 0 3 117 127 119
		mc 0 3 490 533 496
		f 3 286 -277 287
		mu 0 3 128 120 123
		mc 0 3 537 507 517
		f 3 -287 288 -281
		mu 0 3 120 128 125
		mc 0 3 508 538 525
		f 3 -283 289 -288
		mu 0 3 123 126 128
		mc 0 3 518 529 539
		f 3 290 -282 291
		mu 0 3 129 126 124
		mc 0 3 544 530 521
		f 3 292 -290 -291
		mu 0 3 129 128 126
		mc 0 3 545 540 531
		f 3 293 294 -292
		mu 0 3 124 130 129
		mc 0 3 522 551 546
		f 3 295 -295 296
		mu 0 3 131 129 130
		mc 0 3 553 547 552
		f 3 297 298 -289
		mu 0 3 128 132 125
		mc 0 3 541 557 526
		f 3 -299 299 -284
		mu 0 3 125 132 127
		mc 0 3 527 558 534
		f 3 -296 300 301
		mu 0 3 129 131 133
		mc 0 3 548 554 565
		f 3 302 303 -293
		mu 0 3 129 134 128
		mc 0 3 549 568 542
		f 3 -303 -302 304
		mu 0 3 134 129 133
		mc 0 3 569 550 566
		f 3 -305 -301 305
		mu 0 3 134 133 131
		mc 0 3 570 567 555
		f 3 -298 -304 306
		mu 0 3 132 128 134
		mc 0 3 559 543 571
		f 3 -306 307 308
		mu 0 3 134 131 135
		mc 0 3 572 556 574
		f 3 -307 -309 309
		mu 0 3 132 134 135
		mc 0 3 560 573 575
		f 3 -310 310 311
		mu 0 3 132 135 136
		mc 0 3 561 576 577
		f 3 312 -312 313
		mu 0 3 137 132 136
		mc 0 3 579 562 578
		f 3 -313 314 315
		mu 0 3 132 137 138
		mc 0 3 563 580 582
		f 3 316 -300 -316
		mu 0 3 138 127 132
		mc 0 3 583 535 564
		f 3 317 -315 318
		mu 0 3 139 138 137
		mc 0 3 588 584 581
		f 3 319 -286 -317
		mu 0 3 138 119 127
		mc 0 3 585 497 536
		f 3 -318 320 321
		mu 0 3 138 139 140
		mc 0 3 586 589 591
		f 3 322 -320 -322
		mu 0 3 140 119 138
		mc 0 3 592 498 587
		f 3 323 -321 324
		mu 0 3 141 140 139
		mc 0 3 596 593 590
		f 3 325 -323 326
		mu 0 3 142 119 140
		mc 0 3 600 499 594
		f 3 -324 327 -327
		mu 0 3 140 141 142
		mc 0 3 595 597 601
		f 3 -326 328 329
		mu 0 3 119 142 143
		mc 0 3 500 602 605
		f 3 -267 -330 330
		mu 0 3 116 119 143
		mc 0 3 480 501 606
		f 3 331 -328 332
		mu 0 3 144 142 141
		mc 0 3 610 603 598
		f 3 333 -329 -332
		mu 0 3 144 143 142
		mc 0 3 611 607 604
		f 3 -333 334 335
		mu 0 3 144 141 145
		mc 0 3 612 599 616
		f 3 336 -331 337
		mu 0 3 146 116 143
		mc 0 3 619 481 608
		f 3 -334 338 -338
		mu 0 3 143 144 146
		mc 0 3 609 613 620
		f 3 339 -336 340
		mu 0 3 147 144 145
		mc 0 3 625 614 617
		f 3 341 -339 -340
		mu 0 3 147 146 144
		mc 0 3 626 621 615
		f 3 -341 342 343
		mu 0 3 147 145 148
		mc 0 3 627 618 632
		f 3 344 -344 345
		mu 0 3 149 147 148
		mc 0 3 634 628 633
		f 3 346 -337 347
		mu 0 3 150 116 146
		mc 0 3 637 482 622
		f 3 -262 -347 348
		mu 0 3 113 116 150
		mc 0 3 463 483 638
		f 3 -342 349 350
		mu 0 3 146 147 151
		mc 0 3 623 629 642
		f 3 -351 351 -348
		mu 0 3 146 151 150
		mc 0 3 624 643 639
		f 3 -345 352 353
		mu 0 3 147 149 152
		mc 0 3 630 635 648
		f 3 354 -350 -354
		mu 0 3 152 151 147
		mc 0 3 649 644 631
		f 3 355 -353 356
		mu 0 3 59 152 149
		mc 0 3 192 650 636
		f 3 -356 -113 357
		mu 0 3 152 59 58
		mc 0 3 651 193 188
		f 3 358 -352 359
		mu 0 3 153 150 151
		mc 0 3 655 640 645
		f 3 -349 -359 360
		mu 0 3 113 150 153
		mc 0 3 464 641 656
		f 3 -355 361 362
		mu 0 3 151 152 154
		mc 0 3 646 652 661
		f 3 -363 363 -360
		mu 0 3 151 154 153
		mc 0 3 647 662 657
		f 3 -358 364 365
		mu 0 3 152 58 155
		mc 0 3 653 189 666
		f 3 -362 -366 366
		mu 0 3 154 152 155
		mc 0 3 663 654 667
		f 3 -117 367 -365
		mu 0 3 58 60 155
		mc 0 3 190 197 668
		f 3 368 -364 369
		mu 0 3 156 153 154
		mc 0 3 672 658 664
		f 3 -367 370 -370
		mu 0 3 154 155 156
		mc 0 3 665 669 673
		f 3 371 -361 372
		mu 0 3 157 113 153
		mc 0 3 678 465 659
		f 3 -373 -369 373
		mu 0 3 157 153 156
		mc 0 3 679 660 674
		f 3 -372 374 -254
		mu 0 3 113 157 102
		mc 0 3 466 680 411
		f 3 -223 -375 375
		mu 0 3 100 102 157
		mc 0 3 397 412 681
		f 3 376 -226 -376
		mu 0 3 157 103 100
		mc 0 3 682 415 398
		f 3 -374 377 -377
		mu 0 3 157 156 103
		mc 0 3 683 675 416
		f 3 -371 378 379
		mu 0 3 156 155 158
		mc 0 3 676 670 684
		f 3 -380 380 -378
		mu 0 3 156 158 103
		mc 0 3 677 685 417
		f 3 -368 381 -379
		mu 0 3 155 60 158
		mc 0 3 671 198 686
		f 3 -381 382 -228
		mu 0 3 103 158 78
		mc 0 3 418 687 287
		f 3 -382 -120 383
		mu 0 3 158 60 61
		mc 0 3 688 199 204
		f 3 -384 -161 -383
		mu 0 3 158 61 78
		mc 0 3 689 205 288
		f 3 384 385 386
		mu 0 3 159 160 161
		mc 0 3 690 691 694
		f 3 -386 387 388
		mu 0 3 161 160 162
		mc 0 3 695 692 697
		f 3 -389 389 390
		mu 0 3 161 162 163
		mc 0 3 696 698 703
		f 3 391 -388 392
		mu 0 3 164 162 160
		mc 0 3 706 699 693
		f 3 393 -390 394
		mu 0 3 165 163 162
		mc 0 3 709 704 700
		f 3 -394 395 396
		mu 0 3 163 165 166
		mc 0 3 705 710 715
		f 3 397 -396 398
		mu 0 3 167 166 165
		mc 0 3 717 716 711
		f 3 -392 399 400
		mu 0 3 162 164 168
		mc 0 3 701 707 720
		f 3 -401 401 -395
		mu 0 3 162 168 165
		mc 0 3 702 721 712
		f 3 402 -400 403
		mu 0 3 169 168 164
		mc 0 3 726 722 708
		f 3 404 405 -399
		mu 0 3 165 170 167
		mc 0 3 713 729 718
		f 3 -405 -402 406
		mu 0 3 170 165 168
		mc 0 3 730 714 723
		f 3 407 -406 408
		mu 0 3 171 167 170
		mc 0 3 735 719 731
		f 3 409 -403 410
		mu 0 3 172 168 169
		mc 0 3 738 724 727
		f 3 -410 411 -407
		mu 0 3 168 172 170
		mc 0 3 725 739 732
		f 3 412 -411 413
		mu 0 3 173 172 169
		mc 0 3 744 740 728
		f 3 414 415 -409
		mu 0 3 170 174 171
		mc 0 3 733 747 736
		f 3 -415 -412 416
		mu 0 3 174 170 172
		mc 0 3 748 734 741
		f 3 417 -416 418
		mu 0 3 175 171 174
		mc 0 3 753 737 749
		f 3 419 -413 420
		mu 0 3 176 172 173
		mc 0 3 756 742 745
		f 3 421 -417 -420
		mu 0 3 176 174 172
		mc 0 3 757 750 743
		f 3 422 423 -421
		mu 0 3 173 177 176
		mc 0 3 746 762 758
		f 3 424 -419 425
		mu 0 3 178 175 174
		mc 0 3 765 754 751
		f 3 -426 -422 426
		mu 0 3 178 174 176
		mc 0 3 766 752 759
		f 3 427 -425 428
		mu 0 3 179 175 178
		mc 0 3 771 755 767
		f 3 429 -424 430
		mu 0 3 180 176 177
		mc 0 3 774 760 763
		f 3 431 -427 -430
		mu 0 3 180 178 176
		mc 0 3 775 768 761
		f 3 432 433 -431
		mu 0 3 177 181 180
		mc 0 3 764 780 776
		f 3 434 -429 435
		mu 0 3 182 179 178
		mc 0 3 783 772 769
		f 3 -432 436 -436
		mu 0 3 178 180 182
		mc 0 3 770 777 784
		f 3 -435 437 438
		mu 0 3 179 182 183
		mc 0 3 773 785 789
		f 3 439 -434 440
		mu 0 3 184 180 181
		mc 0 3 794 778 781
		f 3 441 -437 -440
		mu 0 3 184 182 180
		mc 0 3 795 786 779
		f 3 442 443 -441
		mu 0 3 181 185 184
		mc 0 3 782 800 796
		f 3 -442 444 445
		mu 0 3 182 184 186
		mc 0 3 787 797 803
		f 3 446 -438 -446
		mu 0 3 186 183 182
		mc 0 3 804 790 788
		f 3 -444 447 448
		mu 0 3 184 185 187
		mc 0 3 798 801 809
		f 3 449 -445 -449
		mu 0 3 187 186 184
		mc 0 3 810 805 799
		f 3 450 451 -448
		mu 0 3 185 188 187
		mc 0 3 802 815 811
		f 3 -447 452 453
		mu 0 3 183 186 189
		mc 0 3 791 806 818
		f 3 -452 454 455
		mu 0 3 187 188 190
		mc 0 3 812 816 823
		f 3 456 457 -455
		mu 0 3 188 191 190
		mc 0 3 817 829 824
		f 3 -450 458 459
		mu 0 3 186 187 192
		mc 0 3 807 813 832
		f 3 -456 460 -459
		mu 0 3 187 190 192
		mc 0 3 814 825 833
		f 3 -460 461 -453
		mu 0 3 186 192 189
		mc 0 3 808 834 819
		f 3 -458 462 463
		mu 0 3 190 191 193
		mc 0 3 826 830 838
		f 3 464 -463 465
		mu 0 3 194 193 191
		mc 0 3 844 839 831
		f 3 -461 466 467
		mu 0 3 192 190 195
		mc 0 3 835 827 847
		f 3 -464 468 -467
		mu 0 3 190 193 195
		mc 0 3 828 840 848
		f 3 -462 469 470
		mu 0 3 189 192 196
		mc 0 3 820 836 853
		f 3 -468 471 -470
		mu 0 3 192 195 196
		mc 0 3 837 849 854
		f 3 472 -454 473
		mu 0 3 197 183 189
		mc 0 3 860 792 821
		f 3 474 -474 -471
		mu 0 3 196 197 189
		mc 0 3 855 861 822
		f 3 -473 475 476
		mu 0 3 183 197 198
		mc 0 3 793 862 867
		f 3 -465 477 478
		mu 0 3 193 194 199
		mc 0 3 841 845 872
		f 3 479 -478 480
		mu 0 3 200 199 194
		mc 0 3 878 873 846
		f 3 481 -469 482
		mu 0 3 201 195 193
		mc 0 3 881 850 842
		f 3 -479 483 -483
		mu 0 3 193 199 201
		mc 0 3 843 874 882
		f 3 484 -480 485
		mu 0 3 202 199 200
		mc 0 3 887 875 879
		f 3 486 -486 487
		mu 0 3 203 202 200
		mc 0 3 893 888 880
		f 3 488 -484 489
		mu 0 3 204 201 199
		mc 0 3 896 883 876
		f 3 -485 490 -490
		mu 0 3 199 202 204
		mc 0 3 877 889 897
		f 3 -482 491 492
		mu 0 3 195 201 205
		mc 0 3 851 884 902
		f 3 -472 -493 493
		mu 0 3 196 195 205
		mc 0 3 856 852 903
		f 3 494 -487 495
		mu 0 3 206 202 203
		mc 0 3 908 890 894
		f 3 496 497 -496
		mu 0 3 203 207 206
		mc 0 3 895 914 909
		f 3 498 499 -495
		mu 0 3 206 208 202
		mc 0 3 910 918 891
		f 3 500 -491 -500
		mu 0 3 208 204 202
		mc 0 3 919 898 892
		f 3 501 -498 502
		mu 0 3 209 206 207
		mc 0 3 924 911 915
		f 3 -489 503 504
		mu 0 3 201 204 210
		mc 0 3 885 899 930
		f 3 505 -492 -505
		mu 0 3 210 205 201
		mc 0 3 931 904 886
		f 3 -501 506 507
		mu 0 3 204 208 211
		mc 0 3 900 920 936
		f 3 508 -504 -508
		mu 0 3 211 210 204
		mc 0 3 937 932 901
		f 3 -499 509 510
		mu 0 3 208 206 212
		mc 0 3 921 912 942
		f 3 511 -510 -502
		mu 0 3 209 212 206
		mc 0 3 925 943 913
		f 3 512 -507 513
		mu 0 3 213 211 208
		mc 0 3 948 938 922
		f 3 514 -514 -511
		mu 0 3 212 213 208
		mc 0 3 944 949 923
		f 3 515 -509 516
		mu 0 3 214 210 211
		mc 0 3 954 933 939
		f 3 517 -513 518
		mu 0 3 215 211 213
		mc 0 3 960 940 950
		f 3 -518 519 -517
		mu 0 3 211 215 214
		mc 0 3 941 961 955
		f 3 -515 520 521
		mu 0 3 213 212 216
		mc 0 3 951 945 966
		f 3 -516 522 523
		mu 0 3 210 214 217
		mc 0 3 934 956 972
		f 3 524 -506 -524
		mu 0 3 217 205 210
		mc 0 3 973 905 935
		f 3 525 526 -519
		mu 0 3 213 218 215
		mc 0 3 952 978 962
		f 3 -526 -522 527
		mu 0 3 218 213 216
		mc 0 3 979 953 967
		f 3 -525 528 529
		mu 0 3 205 217 219
		mc 0 3 906 974 984
		f 3 530 -494 -530
		mu 0 3 219 196 205
		mc 0 3 985 857 907
		f 3 -531 531 532
		mu 0 3 196 219 220
		mc 0 3 858 986 990
		f 3 -475 -533 533
		mu 0 3 197 196 220
		mc 0 3 863 859 991
		f 3 -532 534 535
		mu 0 3 220 219 221
		mc 0 3 992 987 994
		f 3 536 -534 -536
		mu 0 3 221 197 220
		mc 0 3 995 864 993
		f 3 537 538 -529
		mu 0 3 217 222 219
		mc 0 3 975 1000 988
		f 3 539 -535 -539
		mu 0 3 222 221 219
		mc 0 3 1001 996 989
		f 3 -537 540 541
		mu 0 3 197 221 223
		mc 0 3 865 997 1006
		f 3 542 -476 -542
		mu 0 3 223 198 197
		mc 0 3 1007 868 866
		f 3 543 544 -540
		mu 0 3 222 224 221
		mc 0 3 1002 1012 998
		f 3 545 -541 -545
		mu 0 3 224 223 221
		mc 0 3 1013 1008 999
		f 3 546 -538 547
		mu 0 3 225 222 217
		mc 0 3 1020 1003 976
		f 3 548 -548 -523
		mu 0 3 214 225 217
		mc 0 3 957 1021 977
		f 3 549 -544 550
		mu 0 3 226 224 222
		mc 0 3 1026 1014 1004
		f 3 551 -551 -547
		mu 0 3 225 226 222
		mc 0 3 1022 1027 1005
		f 3 -549 552 553
		mu 0 3 225 214 227
		mc 0 3 1023 958 1032
		f 3 554 -553 -520
		mu 0 3 215 227 214
		mc 0 3 963 1033 959
		f 3 555 -552 556
		mu 0 3 228 226 225
		mc 0 3 1038 1028 1024
		f 3 -554 557 -557
		mu 0 3 225 227 228
		mc 0 3 1025 1034 1039
		f 3 -555 558 559
		mu 0 3 227 215 229
		mc 0 3 1035 964 1043
		f 3 560 -559 -527
		mu 0 3 218 229 215
		mc 0 3 980 1044 965
		f 3 561 -558 562
		mu 0 3 230 228 227
		mc 0 3 1049 1040 1036
		f 3 -560 563 -563
		mu 0 3 227 229 230
		mc 0 3 1037 1045 1050
		f 3 564 -556 565
		mu 0 3 231 226 228
		mc 0 3 1055 1029 1041
		f 3 -562 566 -566
		mu 0 3 228 230 231
		mc 0 3 1042 1051 1056
		f 3 -565 567 568
		mu 0 3 226 231 232
		mc 0 3 1030 1057 1059
		f 3 569 -550 -569
		mu 0 3 232 224 226
		mc 0 3 1060 1015 1031
		f 3 570 -567 571
		mu 0 3 233 231 230
		mc 0 3 1062 1058 1052
		f 3 -570 572 573
		mu 0 3 224 232 234
		mc 0 3 1016 1061 1065
		f 3 574 -574 575
		mu 0 3 235 224 234
		mc 0 3 1067 1017 1066
		f 3 576 -572 577
		mu 0 3 236 233 230
		mc 0 3 1070 1063 1053
		f 3 -578 -564 578
		mu 0 3 236 230 229
		mc 0 3 1071 1054 1046
		f 3 -577 579 580
		mu 0 3 233 236 237
		mc 0 3 1064 1072 1076
		f 3 -575 581 582
		mu 0 3 224 235 238
		mc 0 3 1018 1068 1079
		f 3 -546 -583 583
		mu 0 3 223 224 238
		mc 0 3 1009 1019 1080
		f 3 584 -582 585
		mu 0 3 239 238 235
		mc 0 3 1085 1081 1069
		f 3 586 587 -584
		mu 0 3 238 240 223
		mc 0 3 1082 1089 1010
		f 3 -543 -588 588
		mu 0 3 198 223 240
		mc 0 3 869 1011 1090
		f 3 -585 589 590
		mu 0 3 238 239 241
		mc 0 3 1083 1086 1095
		f 3 -587 -591 591
		mu 0 3 240 238 241
		mc 0 3 1091 1084 1096
		f 3 592 593 594
		mu 0 3 242 198 243
		mc 0 3 1100 870 1101
		f 3 595 -594 -589
		mu 0 3 240 243 198
		mc 0 3 1092 1102 871
		f 3 596 597 -590
		mu 0 3 239 244 241
		mc 0 3 1087 1106 1097
		f 3 -597 598 599
		mu 0 3 244 239 245
		mc 0 3 1107 1088 1112
		f 3 600 601 -592
		mu 0 3 241 246 240
		mc 0 3 1098 1115 1093
		f 3 -596 -602 602
		mu 0 3 243 240 246
		mc 0 3 1103 1094 1116
		f 3 -601 -598 603
		mu 0 3 246 241 244
		mc 0 3 1117 1099 1108
		f 3 604 605 606
		mu 0 3 247 243 248
		mc 0 3 1121 1104 1122
		f 3 607 -606 -603
		mu 0 3 246 248 243
		mc 0 3 1118 1123 1105
		f 3 608 609 -600
		mu 0 3 245 249 244
		mc 0 3 1113 1127 1109
		f 3 -609 610 611
		mu 0 3 249 245 250
		mc 0 3 1128 1114 1132
		f 3 612 613 -604
		mu 0 3 244 251 246
		mc 0 3 1110 1135 1119
		f 3 -613 -610 614
		mu 0 3 251 244 249
		mc 0 3 1136 1111 1129
		f 3 -608 -614 615
		mu 0 3 248 246 251
		mc 0 3 1124 1120 1137
		f 3 616 617 -612
		mu 0 3 250 252 249
		mc 0 3 1133 1141 1130
		f 3 -615 -618 618
		mu 0 3 251 249 252
		mc 0 3 1138 1131 1142
		f 3 -617 619 620
		mu 0 3 252 250 253
		mc 0 3 1143 1134 1147
		f 3 621 -616 622
		mu 0 3 254 248 251
		mc 0 3 1150 1125 1139
		f 3 -623 -619 623
		mu 0 3 254 251 252
		mc 0 3 1151 1140 1144
		f 3 -622 624 625
		mu 0 3 248 254 255
		mc 0 3 1126 1152 1156
		f 3 626 627 -621
		mu 0 3 253 256 252
		mc 0 3 1148 1159 1145
		f 3 -628 628 -624
		mu 0 3 252 256 254
		mc 0 3 1146 1160 1153
		f 3 -627 629 630
		mu 0 3 256 253 257
		mc 0 3 1161 1149 1167
		f 3 631 632 -631
		mu 0 3 257 258 256
		mc 0 3 1168 1169 1162
		f 3 633 -633 634
		mu 0 3 259 256 258
		mc 0 3 1171 1163 1170
		f 3 635 -625 636
		mu 0 3 260 255 254
		mc 0 3 1175 1157 1154
		f 3 -637 -629 637
		mu 0 3 260 254 256
		mc 0 3 1176 1155 1164
		f 3 -636 638 639
		mu 0 3 255 260 261
		mc 0 3 1158 1177 1181
		f 3 640 641 -639
		mu 0 3 260 262 261
		mc 0 3 1178 1183 1182
		f 3 642 643 644
		mu 0 3 262 259 263
		mc 0 3 1184 1172 1187
		f 3 645 646 -638
		mu 0 3 256 264 260
		mc 0 3 1165 1188 1179
		f 3 -641 -647 647
		mu 0 3 262 260 264
		mc 0 3 1185 1180 1189
		f 3 -646 -634 648
		mu 0 3 264 256 259
		mc 0 3 1190 1166 1173
		f 3 -643 -648 -649
		mu 0 3 259 262 264
		mc 0 3 1174 1186 1191
		f 3 649 650 651
		mu 0 3 265 266 267
		mc 0 3 1192 1196 1199
		f 3 652 653 654
		mu 0 3 268 265 269
		mc 0 3 1200 1193 1203
		f 3 -650 655 656
		mu 0 3 266 265 270
		mc 0 3 1197 1194 1204
		f 3 -653 657 -656
		mu 0 3 265 268 270
		mc 0 3 1195 1201 1205
		f 3 658 659 -657
		mu 0 3 270 271 266
		mc 0 3 1206 1210 1198
		f 3 660 -658 661
		mu 0 3 272 270 268
		mc 0 3 1214 1207 1202
		f 3 -661 662 663
		mu 0 3 270 272 273
		mc 0 3 1208 1215 1217
		f 3 -659 -664 664
		mu 0 3 271 270 273
		mc 0 3 1211 1209 1218
		f 3 665 -663 666
		mu 0 3 274 273 272
		mc 0 3 1222 1219 1216
		f 3 667 -665 668
		mu 0 3 275 271 273
		mc 0 3 1225 1212 1220
		f 3 -666 669 -669
		mu 0 3 273 274 275
		mc 0 3 1221 1223 1226
		f 3 670 671 -668
		mu 0 3 275 276 271
		mc 0 3 1227 1231 1213
		f 3 672 -670 673
		mu 0 3 277 275 274
		mc 0 3 1234 1228 1224
		f 3 674 -671 675
		mu 0 3 278 276 275
		mc 0 3 1239 1232 1229
		f 3 -673 676 -676
		mu 0 3 275 277 278
		mc 0 3 1230 1235 1240
		f 3 -675 677 678
		mu 0 3 276 278 279
		mc 0 3 1233 1241 1246
		f 3 679 680 -678
		mu 0 3 278 280 279
		mc 0 3 1242 1248 1247
		f 3 -680 681 682
		mu 0 3 280 278 281
		mc 0 3 1249 1243 1251
		f 3 683 684 -683
		mu 0 3 281 282 280
		mc 0 3 1252 1256 1250
		f 3 685 -677 686
		mu 0 3 283 278 277
		mc 0 3 1259 1244 1236
		f 3 -686 687 -682
		mu 0 3 278 283 281
		mc 0 3 1245 1260 1253
		f 3 -684 688 689
		mu 0 3 282 281 284
		mc 0 3 1257 1254 1266
		f 3 -689 -688 690
		mu 0 3 284 281 283
		mc 0 3 1267 1255 1261
		f 3 691 692 -690
		mu 0 3 284 285 282
		mc 0 3 1268 1272 1258
		f 3 693 694 -687
		mu 0 3 277 286 283
		mc 0 3 1237 1275 1262
		f 3 -694 695 696
		mu 0 3 286 277 287
		mc 0 3 1276 1238 1282
		f 3 -697 697 698
		mu 0 3 286 287 288
		mc 0 3 1277 1283 1284
		f 3 -692 699 700
		mu 0 3 285 284 289
		mc 0 3 1273 1269 1288
		f 3 701 702 -701
		mu 0 3 289 290 285
		mc 0 3 1289 1294 1274
		f 3 703 704 -691
		mu 0 3 283 291 284
		mc 0 3 1263 1298 1270
		f 3 -700 -705 705
		mu 0 3 289 284 291
		mc 0 3 1290 1271 1299
		f 3 706 707 -704
		mu 0 3 283 292 291
		mc 0 3 1264 1303 1300
		f 3 -707 -695 708
		mu 0 3 292 283 286
		mc 0 3 1304 1265 1278
		f 3 -706 709 710
		mu 0 3 289 291 293
		mc 0 3 1291 1301 1309
		f 3 -710 -708 711
		mu 0 3 293 291 292
		mc 0 3 1310 1302 1305
		f 3 -702 712 713
		mu 0 3 290 289 294
		mc 0 3 1295 1292 1315
		f 3 -713 -711 714
		mu 0 3 294 289 293
		mc 0 3 1316 1293 1311
		f 3 715 -714 716
		mu 0 3 295 290 294
		mc 0 3 1320 1296 1317
		f 3 717 718 -716
		mu 0 3 295 296 290
		mc 0 3 1321 1326 1297
		f 3 -715 719 720
		mu 0 3 294 293 297
		mc 0 3 1318 1312 1329
		f 3 -717 -721 721
		mu 0 3 295 294 297
		mc 0 3 1322 1319 1330
		f 3 -712 722 723
		mu 0 3 293 292 298
		mc 0 3 1313 1306 1335
		f 3 -720 -724 724
		mu 0 3 297 293 298
		mc 0 3 1331 1314 1336
		f 3 725 -718 726
		mu 0 3 299 296 295
		mc 0 3 1341 1327 1323
		f 3 -726 727 728
		mu 0 3 296 299 300
		mc 0 3 1328 1342 1347
		f 3 -722 729 730
		mu 0 3 295 297 301
		mc 0 3 1324 1332 1350
		f 3 731 -727 -731
		mu 0 3 301 299 295
		mc 0 3 1351 1343 1325
		f 3 -728 732 733
		mu 0 3 300 299 302
		mc 0 3 1348 1344 1356
		f 3 734 735 -734
		mu 0 3 302 303 300
		mc 0 3 1357 1362 1349
		f 3 -732 736 737
		mu 0 3 299 301 304
		mc 0 3 1345 1352 1365
		f 3 738 -733 -738
		mu 0 3 304 302 299
		mc 0 3 1366 1358 1346
		f 3 -730 739 740
		mu 0 3 301 297 305
		mc 0 3 1353 1333 1371
		f 3 -725 741 -740
		mu 0 3 297 298 305
		mc 0 3 1334 1337 1372
		f 3 742 -737 743
		mu 0 3 306 304 301
		mc 0 3 1377 1367 1354
		f 3 -741 744 -744
		mu 0 3 301 305 306
		mc 0 3 1355 1373 1378
		f 3 -739 745 746
		mu 0 3 302 304 307
		mc 0 3 1359 1368 1383
		f 3 747 -735 748
		mu 0 3 308 303 302
		mc 0 3 1388 1363 1360
		f 3 749 -749 -747
		mu 0 3 307 308 302
		mc 0 3 1384 1389 1361
		f 3 -748 750 751
		mu 0 3 303 308 309
		mc 0 3 1364 1390 1395
		f 3 752 753 -751
		mu 0 3 308 310 309
		mc 0 3 1391 1397 1396
		f 3 754 -746 755
		mu 0 3 311 307 304
		mc 0 3 1400 1385 1369
		f 3 -743 756 -756
		mu 0 3 304 306 311
		mc 0 3 1370 1379 1401
		f 3 757 758 -750
		mu 0 3 307 312 308
		mc 0 3 1386 1406 1392
		f 3 -755 759 760
		mu 0 3 307 311 313
		mc 0 3 1387 1402 1409
		f 3 761 -759 762
		mu 0 3 314 308 312
		mc 0 3 1412 1393 1407
		f 3 -753 -762 763
		mu 0 3 310 308 314
		mc 0 3 1398 1394 1413
		f 3 764 765 -763
		mu 0 3 312 315 314
		mc 0 3 1408 1418 1414
		f 3 766 767 -764
		mu 0 3 314 316 310
		mc 0 3 1415 1421 1399
		f 3 768 -766 769
		mu 0 3 317 314 315
		mc 0 3 1424 1416 1419
		f 3 -767 -769 770
		mu 0 3 316 314 317
		mc 0 3 1422 1417 1425
		f 3 771 772 -770
		mu 0 3 315 318 317
		mc 0 3 1420 1431 1426
		f 3 773 774 -771
		mu 0 3 317 319 316
		mc 0 3 1427 1433 1423
		f 3 775 -773 776
		mu 0 3 320 317 318
		mc 0 3 1435 1428 1432
		f 3 -774 777 778
		mu 0 3 319 317 321
		mc 0 3 1434 1429 1437
		f 3 -776 779 -778
		mu 0 3 317 320 321
		mc 0 3 1430 1436 1438
		f 3 780 -760 781
		mu 0 3 322 313 311
		mc 0 3 1439 1410 1403
		f 3 -781 782 783
		mu 0 3 313 322 323
		mc 0 3 1411 1440 1444
		f 3 784 785 -782
		mu 0 3 311 324 322
		mc 0 3 1404 1447 1441
		f 3 -785 -757 786
		mu 0 3 324 311 306
		mc 0 3 1448 1405 1380
		f 3 787 -783 788
		mu 0 3 325 323 322
		mc 0 3 1453 1445 1442
		f 3 789 -789 -786
		mu 0 3 324 325 322
		mc 0 3 1449 1454 1443
		f 3 790 791 -788
		mu 0 3 325 326 323
		mc 0 3 1455 1459 1446
		f 3 792 793 -787
		mu 0 3 306 327 324
		mc 0 3 1381 1460 1450
		f 3 -745 794 -793
		mu 0 3 306 305 327
		mc 0 3 1382 1374 1461
		f 3 -790 795 796
		mu 0 3 325 324 328
		mc 0 3 1456 1451 1467
		f 3 797 -796 -794
		mu 0 3 327 328 324
		mc 0 3 1462 1468 1452
		f 3 -797 798 799
		mu 0 3 325 328 329
		mc 0 3 1457 1469 1473
		f 3 800 801 -800
		mu 0 3 329 330 325
		mc 0 3 1474 1480 1458
		f 3 -801 802 803
		mu 0 3 330 329 331
		mc 0 3 1481 1475 1482
		f 3 -803 804 805
		mu 0 3 331 329 332
		mc 0 3 1483 1476 1484
		f 3 806 807 -805
		mu 0 3 329 333 332
		mc 0 3 1477 1486 1485
		f 3 -807 808 809
		mu 0 3 333 329 334
		mc 0 3 1487 1478 1489
		f 3 -809 -799 810
		mu 0 3 334 329 328
		mc 0 3 1490 1479 1470
		f 3 811 812 -810
		mu 0 3 334 335 333
		mc 0 3 1491 1495 1488
		f 3 813 814 -811
		mu 0 3 328 336 334
		mc 0 3 1471 1499 1492
		f 3 -798 815 -814
		mu 0 3 328 327 336
		mc 0 3 1472 1463 1500
		f 3 -812 816 817
		mu 0 3 335 334 337
		mc 0 3 1496 1493 1504
		f 3 818 -817 -815
		mu 0 3 336 337 334
		mc 0 3 1501 1505 1494
		f 3 819 -818 820
		mu 0 3 338 335 337
		mc 0 3 1509 1497 1506
		f 3 -820 821 822
		mu 0 3 335 338 339
		mc 0 3 1498 1510 1516
		f 3 823 824 -819
		mu 0 3 336 340 337
		mc 0 3 1502 1519 1507
		f 3 -824 -816 825
		mu 0 3 340 336 327
		mc 0 3 1520 1503 1464
		f 3 -821 -825 826
		mu 0 3 338 337 340
		mc 0 3 1511 1508 1521
		f 3 827 828 829
		mu 0 3 341 342 339
		mc 0 3 1525 1530 1517
		f 3 -830 -822 830
		mu 0 3 341 339 338
		mc 0 3 1526 1518 1512
		f 3 -826 831 832
		mu 0 3 340 327 343
		mc 0 3 1522 1465 1531
		f 3 833 -832 -795
		mu 0 3 305 343 327
		mc 0 3 1375 1532 1466
		f 3 -742 834 -834
		mu 0 3 305 298 343
		mc 0 3 1376 1338 1533
		f 3 835 836 -827
		mu 0 3 340 344 338
		mc 0 3 1523 1537 1513
		f 3 837 -836 -833
		mu 0 3 343 344 340
		mc 0 3 1534 1538 1524;
	setAttr ".fc[500:611]"
		f 3 838 839 -835
		mu 0 3 298 345 343
		mc 0 3 1339 1542 1535
		f 3 -838 -840 840
		mu 0 3 344 343 345
		mc 0 3 1539 1536 1543
		f 3 -723 841 -839
		mu 0 3 298 292 345
		mc 0 3 1340 1307 1544
		f 3 842 -842 -709
		mu 0 3 286 345 292
		mc 0 3 1279 1545 1308
		f 3 843 -837 844
		mu 0 3 346 338 344
		mc 0 3 1549 1514 1540
		f 3 845 -845 -841
		mu 0 3 345 346 344
		mc 0 3 1546 1550 1541
		f 3 -844 846 -831
		mu 0 3 338 346 341
		mc 0 3 1515 1551 1527
		f 3 -843 847 848
		mu 0 3 345 286 347
		mc 0 3 1547 1280 1556
		f 3 -846 -849 849
		mu 0 3 346 345 347
		mc 0 3 1552 1548 1557
		f 3 850 -848 -699
		mu 0 3 288 347 286
		mc 0 3 1285 1558 1281
		f 3 851 -850 -851
		mu 0 3 288 346 347
		mc 0 3 1286 1553 1559
		f 3 -852 852 853
		mu 0 3 346 288 348
		mc 0 3 1554 1287 1560
		f 3 854 -847 -854
		mu 0 3 348 341 346
		mc 0 3 1561 1528 1555
		f 3 -855 855 856
		mu 0 3 341 348 349
		mc 0 3 1529 1562 1563
		f 3 857 858 859
		mu 0 3 350 351 352
		mc 0 3 1564 1569 1572
		f 3 -858 860 861
		mu 0 3 351 350 353
		mc 0 3 1570 1565 1573
		f 3 862 863 -862
		mu 0 3 353 354 351
		mc 0 3 1574 1579 1571
		f 3 -863 864 865
		mu 0 3 354 353 355
		mc 0 3 1580 1575 1582
		f 3 866 867 -866
		mu 0 3 355 356 354
		mc 0 3 1583 1588 1581
		f 3 868 -861 869
		mu 0 3 357 353 350
		mc 0 3 1591 1576 1566
		f 3 -867 870 871
		mu 0 3 356 355 358
		mc 0 3 1589 1584 1597
		f 3 872 873 -872
		mu 0 3 358 359 356
		mc 0 3 1598 1603 1590
		f 3 874 -865 875
		mu 0 3 360 355 353
		mc 0 3 1606 1585 1577
		f 3 -869 876 -876
		mu 0 3 353 357 360
		mc 0 3 1578 1592 1607
		f 3 877 -871 878
		mu 0 3 361 358 355
		mc 0 3 1612 1599 1586
		f 3 -875 879 -879
		mu 0 3 355 360 361
		mc 0 3 1587 1608 1613
		f 3 -873 880 881
		mu 0 3 359 358 362
		mc 0 3 1604 1600 1618
		f 3 882 883 -882
		mu 0 3 362 363 359
		mc 0 3 1619 1624 1605
		f 3 -878 884 885
		mu 0 3 358 361 364
		mc 0 3 1601 1614 1627
		f 3 886 -881 -886
		mu 0 3 364 362 358
		mc 0 3 1628 1620 1602
		f 3 887 -880 888
		mu 0 3 365 361 360
		mc 0 3 1633 1615 1609
		f 3 -888 889 890
		mu 0 3 361 365 366
		mc 0 3 1616 1634 1636
		f 3 891 -885 -891
		mu 0 3 366 364 361
		mc 0 3 1637 1629 1617
		f 3 892 893 -889
		mu 0 3 360 367 365
		mc 0 3 1610 1639 1635
		f 3 -893 -877 894
		mu 0 3 367 360 357
		mc 0 3 1640 1611 1593
		f 3 -892 895 896
		mu 0 3 364 366 368
		mc 0 3 1630 1638 1642
		f 3 897 898 -895
		mu 0 3 357 369 367
		mc 0 3 1594 1646 1641
		f 3 899 900 -897
		mu 0 3 368 370 364
		mc 0 3 1643 1651 1631
		f 3 -887 -901 901
		mu 0 3 362 364 370
		mc 0 3 1621 1632 1652
		f 3 -898 902 903
		mu 0 3 369 357 371
		mc 0 3 1647 1595 1657
		f 3 -903 -870 904
		mu 0 3 371 357 350
		mc 0 3 1658 1596 1567
		f 3 -905 905 906
		mu 0 3 371 350 372
		mc 0 3 1659 1568 1663
		f 3 -904 907 908
		mu 0 3 369 371 373
		mc 0 3 1648 1660 1666
		f 3 909 910 -907
		mu 0 3 372 374 371
		mc 0 3 1664 1670 1661
		f 3 -908 -911 911
		mu 0 3 373 371 374
		mc 0 3 1667 1662 1671
		f 3 -910 912 913
		mu 0 3 374 372 375
		mc 0 3 1672 1665 1677
		f 3 914 -914 915
		mu 0 3 376 374 375
		mc 0 3 1679 1673 1678
		f 3 916 -909 917
		mu 0 3 377 369 373
		mc 0 3 1682 1649 1668
		f 3 -918 -912 918
		mu 0 3 377 373 374
		mc 0 3 1683 1669 1674
		f 3 -917 919 920
		mu 0 3 369 377 378
		mc 0 3 1650 1684 1688
		f 3 -915 921 922
		mu 0 3 374 376 379
		mc 0 3 1675 1680 1691
		f 3 -923 923 -919
		mu 0 3 374 379 377
		mc 0 3 1676 1692 1685
		f 3 924 -922 925
		mu 0 3 380 379 376
		mc 0 3 1697 1693 1681
		f 3 926 -920 927
		mu 0 3 381 378 377
		mc 0 3 1701 1689 1686
		f 3 -928 -924 928
		mu 0 3 381 377 379
		mc 0 3 1702 1687 1694
		f 3 -927 929 930
		mu 0 3 378 381 382
		mc 0 3 1690 1703 1707
		f 3 -925 931 932
		mu 0 3 379 380 383
		mc 0 3 1695 1698 1710
		f 3 -933 933 -929
		mu 0 3 379 383 381
		mc 0 3 1696 1711 1704
		f 3 934 935 -930
		mu 0 3 381 384 382
		mc 0 3 1705 1715 1708
		f 3 -934 936 -935
		mu 0 3 381 383 384
		mc 0 3 1706 1712 1716
		f 3 -936 937 938
		mu 0 3 382 384 385
		mc 0 3 1709 1717 1721
		f 3 939 940 -932
		mu 0 3 380 386 383
		mc 0 3 1699 1724 1713
		f 3 -941 941 -937
		mu 0 3 383 386 384
		mc 0 3 1714 1725 1718
		f 3 -940 942 943
		mu 0 3 386 380 387
		mc 0 3 1726 1700 1730
		f 3 944 945 -938
		mu 0 3 384 388 385
		mc 0 3 1719 1733 1722
		f 3 -942 946 -945
		mu 0 3 384 386 388
		mc 0 3 1720 1727 1734
		f 3 -946 947 948
		mu 0 3 385 388 389
		mc 0 3 1723 1735 1739
		f 3 949 950 -944
		mu 0 3 387 390 386
		mc 0 3 1731 1744 1728
		f 3 -951 951 -947
		mu 0 3 386 390 388
		mc 0 3 1729 1745 1736
		f 3 -950 952 953
		mu 0 3 390 387 391
		mc 0 3 1746 1732 1750
		f 3 -952 954 955
		mu 0 3 388 390 392
		mc 0 3 1737 1747 1753
		f 3 -956 956 -948
		mu 0 3 388 392 389
		mc 0 3 1738 1754 1740
		f 3 957 958 -954
		mu 0 3 391 393 390
		mc 0 3 1751 1759 1748
		f 3 959 -955 -959
		mu 0 3 393 392 390
		mc 0 3 1760 1755 1749
		f 3 -958 960 961
		mu 0 3 393 391 394
		mc 0 3 1761 1752 1765
		f 3 962 -957 963
		mu 0 3 395 389 392
		mc 0 3 1768 1741 1756
		f 3 964 965 -962
		mu 0 3 394 396 393
		mc 0 3 1766 1775 1762
		f 3 -965 966 967
		mu 0 3 396 394 397
		mc 0 3 1776 1767 1782
		f 3 968 -968 969
		mu 0 3 237 396 397
		mc 0 3 1077 1777 1783
		f 3 -969 -580 970
		mu 0 3 396 237 236
		mc 0 3 1778 1078 1073
		f 3 -960 971 972
		mu 0 3 392 393 398
		mc 0 3 1757 1763 1784
		f 3 973 -972 -966
		mu 0 3 396 398 393
		mc 0 3 1779 1785 1764
		f 3 -973 974 -964
		mu 0 3 392 398 395
		mc 0 3 1758 1786 1769
		f 3 975 976 -971
		mu 0 3 236 399 396
		mc 0 3 1074 1790 1780
		f 3 -974 -977 977
		mu 0 3 398 396 399
		mc 0 3 1787 1781 1791
		f 3 978 -976 -579
		mu 0 3 229 399 236
		mc 0 3 1047 1792 1075
		f 3 -561 979 -979
		mu 0 3 229 218 399
		mc 0 3 1048 981 1793
		f 3 -978 980 981
		mu 0 3 398 399 400
		mc 0 3 1788 1794 1796
		f 3 982 -981 -980
		mu 0 3 218 400 399
		mc 0 3 982 1797 1795
		f 3 983 -975 -982
		mu 0 3 400 395 398
		mc 0 3 1798 1770 1789
		f 3 -983 -528 984
		mu 0 3 400 218 216
		mc 0 3 1799 983 968
		f 3 985 -984 986
		mu 0 3 401 395 400
		mc 0 3 1802 1771 1800
		f 3 -985 987 -987
		mu 0 3 400 216 401
		mc 0 3 1801 969 1803
		f 3 -986 988 989
		mu 0 3 395 401 402
		mc 0 3 1772 1804 1807
		f 3 990 991 -988
		mu 0 3 216 403 401
		mc 0 3 970 1812 1805
		f 3 992 -989 -992
		mu 0 3 403 402 401
		mc 0 3 1813 1808 1806
		f 3 -991 -521 993
		mu 0 3 403 216 212
		mc 0 3 1814 971 946
		f 3 -512 994 -994
		mu 0 3 212 209 403
		mc 0 3 947 926 1815
		f 3 995 -990 996
		mu 0 3 404 395 402
		mc 0 3 1818 1773 1809
		f 3 -996 997 -963
		mu 0 3 395 404 389
		mc 0 3 1774 1819 1742
		f 3 998 -998 999
		mu 0 3 368 389 404
		mc 0 3 1644 1743 1820
		f 3 -900 -1000 1000
		mu 0 3 370 368 404
		mc 0 3 1653 1645 1821
		f 3 -993 1001 1002
		mu 0 3 402 403 405
		mc 0 3 1810 1816 1824
		f 3 1003 -997 -1003
		mu 0 3 405 404 402
		mc 0 3 1825 1822 1811
		f 3 1004 -1002 -995
		mu 0 3 209 405 403
		mc 0 3 927 1826 1817
		f 3 -1004 1005 -1001
		mu 0 3 404 405 370
		mc 0 3 1823 1827 1654
		f 3 -1005 1006 1007
		mu 0 3 405 209 406
		mc 0 3 1828 928 1830
		f 3 1008 -1006 -1008
		mu 0 3 406 370 405
		mc 0 3 1831 1655 1829
		f 3 1009 -1007 -503
		mu 0 3 207 406 209
		mc 0 3 916 1832 929
		f 3 -1009 1010 -902
		mu 0 3 370 406 362
		mc 0 3 1656 1833 1622
		f 3 -1010 1011 1012
		mu 0 3 406 207 363
		mc 0 3 1834 917 1625
		f 3 -883 -1011 -1013
		mu 0 3 363 362 406
		mc 0 3 1626 1623 1835;
	setAttr ".cd" -type "dataPolyComponent" Index_Data Edge 0 ;
	setAttr ".cvd" -type "dataPolyComponent" Index_Data Vertex 0 ;
	setAttr ".pd[0]" -type "dataPolyComponent" Index_Data UV 0 ;
	setAttr ".hfd" -type "dataPolyComponent" Index_Data Face 0 ;
	setAttr ".ndt" 0;
createNode skinCluster -n "skinCluster1";
	rename -uid "F698CA8F-4606-F982-A5D5-9BB39870BADD";
	setAttr ".ip[0].gtg" -type "string" "skinCluster1";
	setAttr ".skm" -1;
	setAttr -s 407 ".wl";
	setAttr ".wl[0:205].w"
		3 5 0.040650034974514394 6 0.91218433045791603 7 0.047165634567569656
		3 4 0.0063172349608022612 5 0.98722819865076483 6 0.00645456638843295
		3 5 0.0054474711882001323 6 0.98605325363247143 7 0.0084992751793284589
		3 4 0.038971544183154648 5 0.91566338201604891 6 0.045365073800796428
		3 3 0.009613184419495352 4 0.98158236003339527 5 0.0088044555471094316
		3 4 0.0063172349608022612 5 0.98722819865076483 6 0.00645456638843295
		1 21 1
		3 2 0.0098878463110755425 3 0.0010070954576095461 21 0.98910505823131489
		1 21 1
		3 15 0.027435722085048651 16 0.93804837146818987 17 0.034515906446761509
		3 16 0.0045319296865563921 17 0.99150072466371741 18 0.0039673456497262465
		3 16 0.028152896458413963 17 0.94233615434980589 18 0.029510949191780097
		3 17 0.0051728086811028869 18 0.98864728718768813 19 0.0061799041312089863
		3 17 0.030823224294281817 18 0.92782482892764284 19 0.041351946778075396
		3 18 0.0067292287968342959 19 0.98741130687532586 20 0.0058594643278399175
		3 18 0.042236973701636552 19 0.92352178120856165 20 0.034241245089801829
		3 18 0.0035706110747774499 19 0.036469060435144814 20 0.95996032849007773
		2 19 0.0071869996114354547 20 0.99281300038856457
		3 2 0.024231327833037792 3 0.0026855878682001746 21 0.973083084298762
		1 21 1
		1 21 1
		2 2 0.0056610972022900184 21 0.99433890279770998
		3 2 0.92964065074920654 3 0.039414051920175552 21 0.030945297330617905
		3 2 0.9874265661239886 3 0.0088502325826294199 21 0.0037232012933820315
		3 2 0.04100099267067004 3 0.90725566308581329 4 0.05174334424351669
		3 2 0.0064393074218173293 3 0.98236056972481067 4 0.01120012285337201
		3 3 0.056961927138552609 4 0.89781033323846504 5 0.045227739622982294
		3 3 0.009613184419495352 4 0.98158236003339527 5 0.0088044555471094316
		1 22 1
		3 2 0.04100099267067004 3 0.90725566308581329 4 0.05174334424351669
		3 2 0.15060654282569885 3 0.66347754001617432 4 0.18591591715812683
		3 22 0.77877469031177005 23 0.1891050664947192 34 0.032120243193510818
		3 22 0.77575341824340105 23 0.19221789633659545 34 0.03202868542000354
		1 22 1
		1 22 1
		3 22 0.21136796474456787 23 0.62841230630874634 34 0.16021972894668579
		1 23 1
		3 2 0.15060654282569885 3 0.66347754001617432 4 0.18591591715812683
		1 23 1
		3 3 0.18869306709447703 4 0.64972915201572046 5 0.1615777808898026
		3 3 0.056961927138552609 4 0.89781033323846504 5 0.045227739622982294
		1 34 1
		3 23 0.17505149804132428 34 0.67280078936816445 35 0.15214771259051132
		3 34 0.16156252210028535 35 0.65783168845867179 36 0.18060578944104283
		1 34 1
		1 35 1
		3 32 0.16511787966245053 35 0.1807888949152498 36 0.65409322542229964
		3 4 0.15594721072833553 5 0.67357898762194801 6 0.17047380164971651
		3 4 0.038971544183154648 5 0.91566338201604891 6 0.045365073800796428
		3 5 0.040650034974514394 6 0.91218433045791603 7 0.047165634567569656
		1 35 1
		3 5 0.15445181957560508 6 0.67298389483964294 7 0.17256428558475204
		3 6 0.042191195447161878 7 0.91280995099227968 8 0.044998853560558452
		3 6 0.16020447015762329 7 0.67190051078796387 8 0.16789501905441284
		3 7 0.045166704551316585 8 0.92542916019207344 9 0.029404135256610054
		3 32 0.0043183034788619665 35 0.0066071567894792739 36 0.98907453973165871
		1 36 1
		3 7 0.1712520024553538 8 0.70107575360166297 9 0.12767224394298327
		3 8 0.1464255771998402 9 0.74338902150674202 10 0.11018540129341783
		3 8 0.032501716408891351 9 0.94576943625337961 10 0.02172884733772909
		1 32 1
		3 32 0.99436942106956971 33 0.0023346302882271768 36 0.0032959486422030728
		3 32 0.21478599950033425 35 0.24815747881404993 36 0.5370565216856158
		3 32 0.22958723858613911 35 0.28091859398903557 36 0.48949416742482532
		3 32 0.56502632602970826 33 0.19501029863922897 36 0.23996337533106282
		3 32 0.15118639171123505 35 0.16069276630878448 36 0.68812084197998047
		3 32 0.24061951041221619 35 0.29823759198188782 36 0.461142897605896
		3 32 0.040115966795146958 35 0.038941025153681259 36 0.9209430080511718
		3 32 0.23952086626769403 35 0.30365452622852512 36 0.45682460750378084
		3 32 0.86941329357812902 33 0.042725260186654249 36 0.087861446235216689
		3 32 0.46468299627304077 33 0.24242007732391357 36 0.29289692640304565
		3 32 0.44939345121383667 33 0.24974441528320312 36 0.30086213350296021
		3 32 0.743801014359318 33 0.10421911860002098 36 0.15197986704066099
		3 32 0.59421682357788086 33 0.19822995364665985 36 0.20755322277545929
		3 32 0.37557029724121094 33 0.30295261740684509 36 0.32147708535194397
		3 31 0.034088655544325955 32 0.069047069496354391 33 0.89686427495931964
		3 31 0.091645689184154402 32 0.14575417556992434 33 0.7626001352459213
		3 32 0.39501029253005981 33 0.30249485373497009 36 0.30249485373497009
		3 31 0.1948729695417592 32 0.24002441048549383 33 0.56510261997274702
		3 31 0.28676280379295349 32 0.31615167856216431 33 0.3970855176448822
		3 31 0.29948882161047524 32 0.3212176657085915 33 0.37929351268093325
		3 31 0.16101319847981335 32 0.24989699945007265 33 0.58908980207011397
		3 26 0.27597466933651771 31 0.4110933068720492 33 0.31293202379143309
		3 26 0.29237812757492065 31 0.38768595457077026 33 0.31993591785430908
		3 26 0.13389791747775551 31 0.64582283267114804 33 0.22027924985109643
		3 26 0.42063018679618835 27 0.27685970067977905 31 0.30251011252403259
		3 26 0.3958800733089447 27 0.29324787855148315 31 0.31087204813957214
		3 26 0.30908674001693726 27 0.39262989163398743 28 0.29828336834907532
		3 26 0.019592584567696601 31 0.9358815920232596 33 0.044525823409043805
		3 26 0.29825284188232298 27 0.41742579885048275 28 0.28432135926719432
		3 27 0.30388342428554821 28 0.39171435261623999 29 0.3044022230982118
		3 26 0.081818878650665283 31 0.7773250937461853 33 0.14085602760314941
		3 27 0.30576028508662328 28 0.41373311240276361 29 0.2805066025106131
		3 27 0.14882123913828252 28 0.66576637821693352 29 0.18541238264478394
		3 27 0.25290301442146301 28 0.48429083824157715 29 0.26280614733695984
		3 28 0.25110247731208801 29 0.49028763175010681 30 0.25860989093780518
		3 26 0.15060654506991125 27 0.71531243198085481 28 0.13408102294923399
		3 26 0.71618218830635072 27 0.12339971490352708 31 0.16041809679012217
		3 26 0.95774776635456615 27 0.017639430404076634 31 0.024612803241357239
		3 26 0.023849851053577311 27 0.95457389104158941 28 0.021576257904833359
		3 26 0.77933929028095927 27 0.097672995994299766 31 0.12298771372474093
		3 27 0.026932174390055564 28 0.94155794557474171 29 0.031509880035202727
		3 26 0.11718929163185632 27 0.77538719103894205 28 0.10742351732920162
		3 26 0.17390707653483978 31 0.59125657651593022 33 0.23483634694923006
		3 28 0.11978331685550547 29 0.81112382983139542 30 0.06909285331309914
		3 28 0.050827801984962853 29 0.92677195261079004 30 0.022400245404247125
		3 28 0.24641794700676045 29 0.50531776265256889 30 0.24826429034067066
		3 27 0.10843060829914652 28 0.77299153228855477 29 0.11857785941229865
		3 28 0.15074387641977896 29 0.74366369079541239 30 0.10559243278480866
		3 28 0.24808117377637068 29 0.50632487973086715 30 0.24559394649276217
		3 27 0.19485771075315145 28 0.60033569930983488 29 0.2048065899370137
		3 28 0.20184634024362741 29 0.6119935926200869 30 0.18616006713628569
		3 28 0.22691691598048555 29 0.55602349507878701 30 0.21705958894072738
		3 26 0.2016937643794347 27 0.61132218275434325 28 0.18698405286622205
		3 28 0.0017395285108039516 29 0.99665827417661346 30 0.0016021973125825871
		3 28 0.15088121592998505 29 0.72686350345611572 30 0.12225528061389923
		3 27 0.0015259022038807139 28 0.9967193102616565 29 0.0017547875344628208
		1 30 1
		3 24 0.1785763339804386 29 0.11076524026121765 30 0.7106584257583437
		1 29 1
		1 24 1
		3 24 0.65011061206624821 25 0.19890135823043226 30 0.15098802970331951
		3 24 0.17619591688817862 25 0.64704357613558217 37 0.17676050697623927
		1 25 1
		3 24 0.030594340335068151 25 0.16330205299505346 37 0.80610360666987835
		1 24 1
		1 37 1
		1 30 1
		1 25 1
		1 37 1
		3 24 0.03059433896739459 25 0.16200503374998387 37 0.80740062728262152
		3 17 0.030823224294281817 18 0.92782482892764284 19 0.041351946778075396
		3 15 0.12610055882038351 16 0.72460516466513769 17 0.14929427651447882
		3 17 0.14084076881408691 18 0.70316624641418457 19 0.15599298477172852
		3 16 0.1335164437664085 17 0.72983901605249923 18 0.13664454018109232
		3 16 0.028152896458413963 17 0.94233615434980589 18 0.029510949191780097
		3 15 0.027435722085048651 16 0.93804837146818987 17 0.034515906446761509
		3 14 0.025635156159741747 15 0.94378576377552947 16 0.030579080064728779
		3 14 0.12411687898287538 15 0.73670557925982538 16 0.13917754175729924
		3 13 0.022934309967351629 14 0.95660334112790724 15 0.02046234890474119
		3 13 0.12207217605465781 14 0.76609445189009939 15 0.11183337205524274
		3 12 0.030731669814304061 13 0.94378576377552947 14 0.025482566410166465
		3 12 0.13955901875106289 13 0.73614098286943841 14 0.12429999837949868
		1 28 1
		3 11 0.12373540458280291 12 0.74196993751846296 13 0.13429465789873407
		3 11 0.025741970070667676 12 0.94509803896733358 13 0.029159990961998734
		1 27 1
		3 10 0.11320668290247496 11 0.76871900605083998 12 0.11807431104668512
		3 10 0.022461280394057037 11 0.95365834946675854 12 0.02388037013918437
		3 9 0.025787746341617804 10 0.95262073760762256 11 0.021591516050759582
		3 26 0.0012664988451444987 27 0.99754329742086434 28 0.0011902037339912156
		1 26 1
		3 9 0.12449835985898972 10 0.76540780067443848 11 0.11009383946657181
		3 26 0.99755855644252645 27 0.0011444266675657035 31 0.0012970168899077972
		1 31 1
		1 33 1
		3 26 0.0015106431684763937 31 0.99613946745833815 33 0.0023498893731855016
		3 26 0.611306923964826 27 0.1797055059583636 31 0.20898757007681043
		3 31 0.0028381781494400565 32 0.0031891356625428592 33 0.99397268618801704
		1 21 1
		1 2 1
		1 21 1
		1 2 1
		1 21 1
		2 3 0.99879453729261447 4 0.0012054627073855247
		2 2 0.99848935686739948 3 0.0015106431326005444
		2 2 0.0056610972022900184 21 0.99433890279770998
		3 2 0.9874265661239886 3 0.0088502325826294199 21 0.0037232012933820315
		1 3 1
		2 3 0.0012970168352484631 4 0.99870298316475159
		3 2 0.0011902037195811886 3 0.99674982830422065 4 0.002059967976198211
		3 2 0.0064393074218173293 3 0.98236056972481067 4 0.01120012285337201
		1 4 1
		1 5 1
		3 3 0.0018463416623968145 4 0.99656672004926217 5 0.0015869382883410637
		3 3 0.009613184419495352 4 0.98158236003339527 5 0.0088044555471094316
		1 5 1
		1 6 1
		3 4 0.0011902037364852588 5 0.99768062861607998 6 0.0011291676474347327
		3 4 0.0063172349608022612 5 0.98722819865076483 6 0.00645456638843295
		1 6 1
		2 6 0.0010681315151114933 7 0.99893186848488846
		3 5 0.0010376135104767084 6 0.99746700231265983 7 0.0014953841768634915
		3 5 0.0054474711882001323 6 0.98605325363247143 7 0.0084992751793284589
		1 7 1
		1 8 1
		3 6 0.0015106431871177671 7 0.99694819558158032 8 0.0015411612313019644
		1 8 1
		1 9 1
		3 6 0.0079957273528616524 7 0.98342870200531629 8 0.0085755706418220602
		1 9 1
		1 10 1
		2 7 0.0014038299840985894 8 0.9985961700159014
		1 10 1
		1 11 1
		1 9 1
		3 7 0.0074769206057804542 8 0.98722819865076483 9 0.005294880743454757
		3 6 0.042191195447161878 7 0.91280995099227968 8 0.044998853560558452
		3 5 0.040650034974514394 6 0.91218433045791603 7 0.047165634567569656
		1 11 1
		1 12 1
		1 10 1
		1 12 1
		1 13 1
		1 11 1
		3 8 0.00453192970554949 9 0.99177538702038326 10 0.003692683274067209;
	setAttr ".wl[206:398].w"
		1 13 1
		1 14 1
		1 12 1
		1 14 1
		3 9 0.0041351951591329728 10 0.99209582643940331 11 0.0037689784014637469
		3 10 0.0031738765944175451 11 0.99302662690553456 12 0.0037994965000479265
		1 13 1
		3 11 0.0036621651946679773 12 0.99111924940293017 13 0.0052185854024018674
		3 10 0.022461280394057037 11 0.95365834946675854 12 0.02388037013918437
		3 11 0.025741970070667676 12 0.94509803896733358 13 0.029159990961998734
		3 12 0.0049439229644557062 13 0.99049362937563878 14 0.0045624476599055025
		3 9 0.025787746341617804 10 0.95262073760762256 11 0.021591516050759582
		3 12 0.030731669814304061 13 0.94378576377552947 14 0.025482566410166465
		3 8 0.032501716408891351 9 0.94576943625337961 10 0.02172884733772909
		3 7 0.045166704551316585 8 0.92542916019207344 9 0.029404135256610054
		3 7 0.043869690087505207 8 0.9273060171449039 9 0.028824292767590867
		3 8 0.031631954603492371 9 0.94665445660528647 10 0.021713588791221171
		3 6 0.0415960933684284 7 0.9157854557428442 8 0.042618450888727441
		3 7 0.020111391882730423 8 0.9667048128332425 9 0.013183795284027102
		3 9 0.024383918086765061 10 0.95489432917632278 11 0.02072175273691218
		3 8 0.014465552404425701 9 0.9750057222785905 10 0.01052872531698378
		3 10 0.021957733268757412 11 0.95471122192450963 12 0.02333104480673295
		3 9 0.010086213323078975 10 0.98101777660582212 11 0.0088960100710988883
		3 11 0.025558860829702424 12 0.94488441416127011 13 0.029556725009027542
		3 10 0.0099183645391723169 11 0.97949187396898696 12 0.010589761491840757
		1 10 1
		1 9 1
		1 11 1
		1 8 1
		2 6 0.0010681315151114933 7 0.99893186848488846
		3 11 0.011825742343193526 12 0.97346456037372286 13 0.014709697283083634
		1 12 1
		3 6 0.022781720257652623 7 0.956679636854606 8 0.02053864288774146
		1 6 1
		3 5 0.038361180573701859 6 0.91795223951339722 7 0.043686579912900925
		3 5 0.020401312190304041 6 0.9575494003113314 7 0.022049287498364503
		3 4 0.0063172349608022612 5 0.98722819865076483 6 0.00645456638843295
		3 4 0.038971544183154648 5 0.91566338201604891 6 0.045365073800796428
		3 4 0.020920117927340456 5 0.95967040658611047 6 0.019409475486549074
		1 5 1
		3 4 0.042420081320180582 5 0.91340505056003052 6 0.0441748681197889
		3 3 0.009613184419495352 4 0.98158236003339527 5 0.0088044555471094316
		3 3 0.056961927138552609 4 0.89781033323846504 5 0.045227739622982294
		3 3 0.025406271550513618 4 0.95393301300244604 5 0.02066071544704029
		2 3 0.0012970168352484631 4 0.99870298316475159
		3 3 0.055085068994777338 4 0.90074006354369063 5 0.044174867461532083
		3 2 0.017135881270525184 3 0.95455863225218573 4 0.028305486477289046
		2 3 0.99879453729261447 4 0.0012054627073855247
		3 2 0.038956283652269462 3 0.90884260291957997 4 0.052201113428150564
		3 2 0.04100099267067004 3 0.90725566308581329 4 0.05174334424351669
		3 2 0.96986343102300709 3 0.016968032629624555 21 0.01316853634736841
		1 2 1
		1 21 1
		3 2 0.0098878463110755425 3 0.0010070954576095461 21 0.98910505823131489
		3 2 0.93284504563162052 3 0.037598229524513006 21 0.029556724843866473
		3 2 0.92964065074920654 3 0.039414051920175552 21 0.030945297330617905
		3 2 0.024231327833037792 3 0.0026855878682001746 21 0.973083084298762
		1 21 1
		3 2 0.023163196260335951 3 0.0025635157401220957 21 0.97427328799954194
		3 24 0.03059433896739459 25 0.16200503374998387 37 0.80740062728262152
		3 16 0.028152896458413963 17 0.94233615434980589 18 0.029510949191780097
		3 17 0.030823224294281817 18 0.92782482892764284 19 0.041351946778075396
		3 24 0.17619591688817862 25 0.64704357613558217 37 0.17676050697623927
		3 24 0.030594340335068151 25 0.16330205299505346 37 0.80610360666987835
		3 24 0.18646525124408678 25 0.63755244966674529 37 0.17598229908916799
		3 15 0.027435722085048651 16 0.93804837146818987 17 0.034515906446761509
		3 24 0.65011061206624821 25 0.19890135823043226 30 0.15098802970331951
		3 24 0.64841687679290771 25 0.19125658273696899 30 0.16032654047012329
		3 24 0.1785763339804386 29 0.11076524026121765 30 0.7106584257583437
		3 24 0.1770351664942863 29 0.11647211673504027 30 0.70649271677067338
		3 14 0.025635156159741747 15 0.94378576377552947 16 0.030579080064728779
		3 28 0.15088121592998505 29 0.72686350345611572 30 0.12225528061389923
		3 28 0.15666437149047852 29 0.72216373682022095 30 0.12117189168930054
		3 13 0.022934309967351629 14 0.95660334112790724 15 0.02046234890474119
		3 12 0.030731669814304061 13 0.94378576377552947 14 0.025482566410166465
		3 27 0.13865873630817938 28 0.70885785546475222 29 0.15248340822706843
		3 11 0.025741970070667676 12 0.94509803896733358 13 0.029159990961998734
		3 27 0.13749904930591583 28 0.71161973476409912 29 0.15088121592998505
		3 26 0.14335851584909134 27 0.71590752476315989 28 0.14073395938774882
		3 10 0.022461280394057037 11 0.95365834946675854 12 0.02388037013918437
		3 27 0.2228580084017216 28 0.5418936529473416 29 0.23524833865093681
		3 28 0.22691691598048555 29 0.55602349507878701 30 0.21705958894072738
		3 28 0.24808117377637068 29 0.50632487973086715 30 0.24559394649276217
		3 26 0.71364920267985466 27 0.14081024913772569 31 0.14554054818241971
		3 9 0.025787746341617804 10 0.95262073760762256 11 0.021591516050759582
		3 26 0.14291599605852359 27 0.71923400043299801 28 0.13785000350847845
		3 26 0.22987715557400651 27 0.55291067730023447 28 0.21721216712575903
		3 26 0.71708247908704048 27 0.13646143268163702 31 0.14645608823132253
		3 26 0.14070344180916908 31 0.68487067051039152 33 0.17442588768043946
		3 31 0.16627756256692297 32 0.16388190281039186 33 0.66984053462268511
		3 8 0.032501716408891351 9 0.94576943625337961 10 0.02172884733772909
		3 26 0.1361562440372073 31 0.68630503585480107 33 0.17753872010799168
		3 26 0.55658807029092516 27 0.20868239428646548 31 0.23472953542260933
		3 32 0.65011061206624821 33 0.16089113296406168 36 0.18899825496969008
		3 7 0.045166704551316585 8 0.92542916019207344 9 0.029404135256610054
		3 31 0.15704585377803662 32 0.16794079291908751 33 0.67501335330287582
		3 32 0.17634851704989324 35 0.17685205707394908 36 0.64679942587615769
		3 6 0.042191195447161878 7 0.91280995099227968 8 0.044998853560558452
		3 32 0.65325398226460785 33 0.15617609256768364 36 0.19056992516770849
		3 26 0.2056000649094572 31 0.52660410811596947 33 0.26779582697457333
		3 31 0.22401769125435217 32 0.26962691143711043 33 0.5063553973085374
		3 32 0.16511787966245053 35 0.1807888949152498 36 0.65409322542229964
		3 34 0.1545433746142201 35 0.65407796663278239 36 0.19137865875299748
		3 5 0.040650034974514394 6 0.91218433045791603 7 0.047165634567569656
		3 4 0.038971544183154648 5 0.91566338201604891 6 0.045365073800796428
		3 32 0.4979018792822677 33 0.22719157893670233 36 0.27490654178102997
		3 34 0.16156252210028535 35 0.65783168845867179 36 0.18060578944104283
		3 32 0.22958723858613911 35 0.28091859398903557 36 0.48949416742482532
		3 23 0.17793544861770497 34 0.6669260760109712 35 0.15513847537132389
		3 23 0.17505149804132428 34 0.67280078936816445 35 0.15214771259051132
		3 3 0.056961927138552609 4 0.89781033323846504 5 0.045227739622982294
		3 22 0.21206989026277931 23 0.62276645370621841 34 0.16516365603100228
		3 22 0.21136796474456787 23 0.62841230630874634 34 0.16021972894668579
		3 2 0.04100099267067004 3 0.90725566308581329 4 0.05174334424351669
		3 22 0.77575341824340105 23 0.19221789633659545 34 0.03202868542000354
		3 22 0.77877469031177005 23 0.1891050664947192 34 0.032120243193510818
		3 32 0.46015106946004825 33 0.24658579756936733 36 0.29326313297058443
		3 32 0.24061951041221619 35 0.29823759198188782 36 0.461142897605896
		3 31 0.23727778736833055 32 0.28896009491443492 33 0.47376211771723453
		3 32 0.46468299627304077 33 0.24242007732391357 36 0.29289692640304565
		3 32 0.23952086626769403 35 0.30365452622852512 36 0.45682460750378084
		3 26 0.22667276859283447 31 0.48519110679626465 33 0.28813612461090088
		3 31 0.23492791108679639 32 0.2934309883926956 33 0.47164110052050801
		3 31 0.24086366234922912 32 0.3045700743113447 33 0.45456626333942618
		3 32 0.44939345121383667 33 0.24974441528320312 36 0.30086213350296021
		3 32 0.37557029724121094 33 0.30295261740684509 36 0.32147708535194397
		3 31 0.29948882161047524 32 0.3212176657085915 33 0.37929351268093325
		3 26 0.29237812757492065 31 0.38768595457077026 33 0.31993591785430908
		3 26 0.2288090356829475 31 0.47336538056628052 33 0.297825583750772
		3 26 0.3958800733089447 27 0.29324787855148315 31 0.31087204813957214
		3 26 0.22082856297492981 31 0.49106582999229431 33 0.28810560703277588
		3 26 0.49538415670394897 27 0.23479056358337402 31 0.269825279712677
		3 26 0.26233309898276774 27 0.49237812299099748 28 0.24528877802623478
		3 26 0.30908674001693726 27 0.39262989163398743 28 0.29828336834907532
		3 26 0.51030749082565308 27 0.22897687554359436 31 0.26071563363075256
		3 27 0.25290301442146301 28 0.48429083824157715 29 0.26280614733695984
		3 27 0.30388342428554821 28 0.39171435261623999 29 0.3044022230982118
		3 26 0.50954449936068802 27 0.23114367173826206 31 0.25931182890104992
		3 26 0.25464254238244083 27 0.50638591488620766 28 0.23897154273135152
		3 26 0.25522240616049757 27 0.50402074301211919 28 0.24075685082738324
		3 27 0.24367133509133265 28 0.5018234402484727 29 0.25450522466019465
		3 27 0.24388495087623596 28 0.50121307373046875 29 0.25490197539329529
		3 28 0.24641794700676045 29 0.50531776265256889 30 0.24826429034067066
		3 28 0.25110247731208801 29 0.49028763175010681 30 0.25860989093780518
		1 20 1
		1 19 1
		1 20 1
		1 19 1
		1 18 1
		1 18 1
		1 17 1
		2 19 0.0012817578139557371 20 0.99871824218604421
		1 17 1
		1 16 1
		3 18 0.0012512398255357848 19 0.99768062861607998 20 0.0010681315583842067
		2 18 0.99885557337799857 19 0.0011444266220014549
		1 16 1
		1 15 1
		1 17 1
		3 18 0.0067292287968342959 19 0.98741130687532586 20 0.0058594643278399175
		3 17 0.0051728086811028869 18 0.98864728718768813 19 0.0061799041312089863
		2 19 0.0071869996114354547 20 0.99281300038856457
		3 16 0.0045319296865563921 17 0.99150072466371741 18 0.0039673456497262465
		3 18 0.0035706110747774499 19 0.036469060435144814 20 0.95996032849007773
		1 16 1
		3 18 0.0014190889974046935 19 0.015930419353801045 20 0.98265049164879426
		1 20 1
		3 18 0.0034485389590914236 19 0.035309378172813752 20 0.96124208286809487
		3 18 0.018295567891647695 19 0.96632333769626932 20 0.015381094412083053
		1 19 1
		1 18 1
		3 18 0.041123062065816951 19 0.92510872390040211 20 0.033768214033780886
		3 18 0.042236973701636552 19 0.92352178120856165 20 0.034241245089801829
		3 17 0.013946746800717591 18 0.96643015012215239 19 0.01962310307713
		1 17 1
		3 17 0.029404135913843703 18 0.93087662826830453 19 0.039719235817851729
		3 17 0.030823224294281817 18 0.92782482892764284 19 0.041351946778075396
		3 16 0.013839932754786451 17 0.97106889519114858 18 0.01509117205406495
		3 16 0.027573053564123443 17 0.94329747212950532 18 0.029129474306371278
		3 16 0.028152896458413963 17 0.94233615434980589 18 0.029510949191780097
		3 15 0.012939650179754193 16 0.97074845520411568 17 0.016311894616130154
		1 16 1
		3 15 0.026550698431938177 16 0.94006256148079281 17 0.033386740087269093
		3 15 0.027435722085048651 16 0.93804837146818987 17 0.034515906446761509
		3 14 0.011200122754278199 15 0.97398336646487071 16 0.014816510780851102
		1 15 1
		3 14 0.024597544223070145 15 0.94540321826934814 16 0.029999237507581711
		3 13 0.012283512448349561 14 0.97685206391314072 15 0.010864423638509696
		1 14 1
		3 14 0.025635156159741747 15 0.94378576377552947 16 0.030579080064728779
		3 12 0.013885710750520136 13 0.97439536012995065 14 0.011718929119529218
		1 13 1
		2 13 0.024185549828194826 14 0.95408560267218356;
	setAttr ".wl[398:406].w"
		1 15 0.021728847499621621
		3 12 0.029877165221135447 13 0.94514381533435055 14 0.024979019444513993
		3 13 0.022934309967351629 14 0.95660334112790724 15 0.02046234890474119
		3 13 0.0032196536786743999 14 0.99339284339873923 15 0.0033875029225863356
		3 14 0.0040131229533523043 15 0.99159227878235023 16 0.0043945982642974862
		1 14 1
		3 15 0.0051422907329429068 16 0.98986800875666947 17 0.0049897005103876468
		1 15 1
		1 15 1;
	setAttr -s 38 ".pm";
	setAttr ".pm[0]" -type "matrix" 1 0 0 0 0 0 1 0 0 -1 0 0 0 0 0 1;
	setAttr ".pm[1]" -type "matrix" 1 0 0 0 0 0 1 0 0 -1 0 0 0 0 0 1;
	setAttr ".pm[2]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -27.614380000000001 -21.471606999999999 2.2410760000000001 1;
	setAttr ".pm[3]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -32.143219000000002 -13.838022 2.1627260000000001 1;
	setAttr ".pm[4]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -34.427424999999999 -6.3767969999999998 2.121378 1;
	setAttr ".pm[5]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -34.898628000000002 1.974307 2.1008749999999998 1;
	setAttr ".pm[6]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -33.341681999999999 10.602084 2.0146380000000002 1;
	setAttr ".pm[7]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -29.906245999999999 18.245142000000001 1.9114549999999999 1;
	setAttr ".pm[8]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -24.603687000000001 25.028238000000002 1.831963 1;
	setAttr ".pm[9]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -16.763134000000001 30.747532 1.7637830000000001 1;
	setAttr ".pm[10]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -6.9746810000000004 34.391983000000003 1.6563600000000001 1;
	setAttr ".pm[11]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 3.7684319999999998 34.805732999999996 1.512705 1;
	setAttr ".pm[12]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 13.814380999999999 32.142569999999999 1.471136 1;
	setAttr ".pm[13]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 22.042953000000001 27.109784999999999 1.402911 1;
	setAttr ".pm[14]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 28.723921000000001 19.588726000000001 1.299372 1;
	setAttr ".pm[15]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 33.321635999999998 10.329469 1.450944 1;
	setAttr ".pm[16]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 34.846767 0.764903 1.454858 1;
	setAttr ".pm[17]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 33.664349000000001 -8.6544489999999996 1.4924390000000001 1;
	setAttr ".pm[18]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 30.092541000000001 -17.568263999999999 1.658792 1;
	setAttr ".pm[19]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 24.680914000000001 -24.582871999999998 1.8051299999999999 1;
	setAttr ".pm[20]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 17.320613999999999 -30.235025 1.9066669999999999 1;
	setAttr ".pm[21]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -20.294837999999999 -28.366350000000001 2.129518 1;
	setAttr ".pm[22]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -16.668509 -8.0662780000000005 -9.6415170000000003 1;
	setAttr ".pm[23]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -18.110230999999999 -3.9437899999999999 -9.8511480000000002 1;
	setAttr ".pm[24]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 18.167266999999999 0.14135400000000001 -10.212529 1;
	setAttr ".pm[25]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 17.628541999999999 -4.3510960000000001 -10.173567 1;
	setAttr ".pm[26]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 1.3722190000000001 18.23143 -10.203543 1;
	setAttr ".pm[27]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 6.6871559999999999 16.998467999999999 -10.237473 1;
	setAttr ".pm[28]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 11.421526 14.212968 -10.246186 1;
	setAttr ".pm[29]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 15.025188999999999 10.376192 -10.233383999999999 1;
	setAttr ".pm[30]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 17.484621000000001 5.0230829999999997 -10.228183 1;
	setAttr ".pm[31]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -4.0030250000000001 17.909624000000001 -10.178516999999999 1;
	setAttr ".pm[32]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -12.715506 13.486855 -9.999568 1;
	setAttr ".pm[33]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -8.6368829999999992 16.305444999999999 -10.077097 1;
	setAttr ".pm[34]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -18.534330000000001 0.79496900000000004 -9.870806 1;
	setAttr ".pm[35]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -17.626439999999999 5.7825090000000001 -9.9140219999999992 1;
	setAttr ".pm[36]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 -15.665008 9.9405619999999999 -9.8610439999999997 1;
	setAttr ".pm[37]" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 15.923617999999999 -8.8678939999999997 -9.9222470000000005 1;
	setAttr ".gm" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr -s 38 ".ma";
	setAttr -s 38 ".dpf[0:37]"  4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 
		4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4;
	setAttr -s 38 ".lw";
	setAttr -s 38 ".lw";
	setAttr ".mi" 5;
	setAttr ".bm" 1;
	setAttr ".ucm" yes;
	setAttr -s 38 ".ifcl";
	setAttr -s 38 ".ifcl";
createNode dagPose -n "bindPose1";
	rename -uid "94F0CFF1-4532-8F46-7439-919102F0EFF1";
	setAttr -s 39 ".wm";
	setAttr ".wm[0]" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr -s 39 ".xm";
	setAttr ".xm[0]" -type "matrix" "xform" 1 1 1 -1.5707963267948966 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 yes;
	setAttr ".xm[1]" -type "matrix" "xform" 1 1 1 0 -0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[2]" -type "matrix" "xform" 1 1 1 0 -0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[3]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 27.614380000000001
		 2.2410760000000001 21.471606999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[4]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 32.143219000000002
		 2.1627260000000001 13.838022 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[5]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 34.427424999999999
		 2.121378 6.3767969999999998 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[6]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 34.898628000000002
		 2.1008749999999998 -1.974307 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[7]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 33.341681999999999
		 2.0146380000000002 -10.602084 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[8]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 29.906245999999999
		 1.9114549999999999 -18.245142000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[9]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 24.603687000000001
		 1.831963 -25.028238000000002 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[10]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 16.763134000000001
		 1.7637830000000001 -30.747532 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[11]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 6.9746810000000004
		 1.6563600000000001 -34.391983000000003 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[12]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -3.7684319999999998
		 1.512705 -34.805732999999996 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[13]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -13.814380999999999
		 1.471136 -32.142569999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[14]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -22.042953000000001
		 1.402911 -27.109784999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[15]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -28.723921000000001
		 1.299372 -19.588726000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[16]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -33.321635999999998
		 1.450944 -10.329469 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[17]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -34.846767
		 1.454858 -0.764903 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[18]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -33.664349000000001
		 1.4924390000000001 8.6544489999999996 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[19]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -30.092541000000001
		 1.658792 17.568263999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[20]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -24.680914000000001
		 1.8051299999999999 24.582871999999998 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[21]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -17.320613999999999
		 1.9066669999999999 30.235025 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[22]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 20.294837999999999
		 2.129518 28.366350000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[23]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 16.668509
		 -9.6415170000000003 8.0662780000000005 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[24]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 18.110230999999999
		 -9.8511480000000002 3.9437899999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[25]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -18.167266999999999
		 -10.212529 -0.14135400000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[26]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -17.628541999999999
		 -10.173567 4.3510960000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[27]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -1.3722190000000001
		 -10.203543 -18.23143 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[28]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -6.6871559999999999
		 -10.237473 -16.998467999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[29]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -11.421526
		 -10.246186 -14.212968 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[30]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -15.025188999999999
		 -10.233383999999999 -10.376192 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[31]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -17.484621000000001
		 -10.228183 -5.0230829999999997 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[32]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 4.0030250000000001
		 -10.178516999999999 -17.909624000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[33]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 12.715506
		 -9.999568 -13.486855 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[34]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 8.6368829999999992
		 -10.077097 -16.305444999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[35]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 18.534330000000001
		 -9.870806 -0.79496900000000004 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1
		 1 no;
	setAttr ".xm[36]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 17.626439999999999
		 -9.9140219999999992 -5.7825090000000001 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[37]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 15.665008
		 -9.8610439999999997 -9.9405619999999999 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[38]" -type "matrix" "xform" 1 1 1 1.5707963267948963 -0 0 0 -15.923617999999999
		 -9.9222470000000005 8.8678939999999997 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr -s 39 ".m";
	setAttr -s 39 ".p";
	setAttr -s 39 ".g[0:38]" yes no no no no no no no no no no no no no 
		no no no no no no no no no no no no no no no no no no no no no no no no no;
	setAttr ".bp" yes;
createNode materialInfo -n "materialInfo2";
	rename -uid "912101D3-41DD-0AFF-D705-B8BEEC2DA94B";
createNode shadingEngine -n "TechLimbShield_MatSG";
	rename -uid "3E9C27A0-4587-1B53-9741-4FB6DFA880EB";
	setAttr ".ihi" 0;
	setAttr ".ro" yes;
createNode lambert -n "TechLimbShield_Mat";
	rename -uid "B8940CA0-4CC2-47B6-8407-4E9FD2DB427D";
createNode lightLinker -s -n "lightLinker1";
	rename -uid "D112F63D-45E5-B546-14A7-CA9AA1B5BF08";
	setAttr -s 4 ".lnk";
	setAttr -s 4 ".slnk";
select -ne :time1;
	setAttr ".o" 0;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".fprt" yes;
	setAttr ".rtfm" 1;
select -ne :renderPartition;
	setAttr -s 4 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 8 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
select -ne :standardSurface1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :openPBR_shader1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :initialShadingGroup;
	setAttr ".ro" yes;
select -ne :initialParticleSE;
	setAttr ".ro" yes;
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :defaultColorMgtGlobals;
	setAttr ".cfe" yes;
	setAttr ".cfp" -type "string" "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio";
	setAttr ".vtn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".vn" -type "string" "ACES 1.0 SDR-video";
	setAttr ".dn" -type "string" "sRGB";
	setAttr ".wsn" -type "string" "ACEScg";
	setAttr ".otn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".potn" -type "string" "ACES 1.0 SDR-video (sRGB)";
select -ne :hardwareRenderGlobals;
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
connectAttr "Root.s" "Main.is";
connectAttr "Main.s" "joint_on_vertex_020.is";
connectAttr "Main.s" "joint_on_vertex_019.is";
connectAttr "Main.s" "joint_on_vertex_018.is";
connectAttr "Main.s" "joint_on_vertex_017.is";
connectAttr "Main.s" "joint_on_vertex_016.is";
connectAttr "Main.s" "joint_on_vertex_015.is";
connectAttr "Main.s" "joint_on_vertex_014.is";
connectAttr "Main.s" "joint_on_vertex_013.is";
connectAttr "Main.s" "joint_on_vertex_012.is";
connectAttr "Main.s" "joint_on_vertex_011.is";
connectAttr "Main.s" "joint_on_vertex_010.is";
connectAttr "Main.s" "joint_on_vertex_009.is";
connectAttr "Main.s" "joint_on_vertex_008.is";
connectAttr "Main.s" "joint_on_vertex_007.is";
connectAttr "Main.s" "joint_on_vertex_006.is";
connectAttr "Main.s" "joint_on_vertex_005.is";
connectAttr "Main.s" "joint_on_vertex_004.is";
connectAttr "Main.s" "joint_on_vertex_003.is";
connectAttr "Main.s" "joint_on_vertex_002.is";
connectAttr "Main.s" "joint_on_vertex_001.is";
connectAttr "Main.s" "joint_on_vertex_021.is";
connectAttr "Main.s" "joint_on_vertex_022.is";
connectAttr "Main.s" "joint_on_vertex_023.is";
connectAttr "Main.s" "joint_on_vertex_024.is";
connectAttr "Main.s" "joint_on_vertex_025.is";
connectAttr "Main.s" "joint_on_vertex_026.is";
connectAttr "Main.s" "joint_on_vertex_027.is";
connectAttr "Main.s" "joint_on_vertex_028.is";
connectAttr "Main.s" "joint_on_vertex_029.is";
connectAttr "Main.s" "joint_on_vertex_030.is";
connectAttr "Main.s" "joint_on_vertex_031.is";
connectAttr "Main.s" "joint_on_vertex_032.is";
connectAttr "Main.s" "joint_on_vertex_033.is";
connectAttr "Main.s" "joint_on_vertex_034.is";
connectAttr "Main.s" "joint_on_vertex_035.is";
connectAttr "Main.s" "joint_on_vertex_036.is";
connectAttr "skinCluster1.og[0]" "TechLimbShieldMeshShape.i";
connectAttr "TechLimbShieldMeshShapeOrig.w" "skinCluster1.ip[0].ig";
connectAttr "TechLimbShieldMeshShapeOrig.o" "skinCluster1.orggeom[0]";
connectAttr "bindPose1.msg" "skinCluster1.bp";
connectAttr "Root.wm" "skinCluster1.ma[0]";
connectAttr "Main.wm" "skinCluster1.ma[1]";
connectAttr "joint_on_vertex_020.wm" "skinCluster1.ma[2]";
connectAttr "joint_on_vertex_019.wm" "skinCluster1.ma[3]";
connectAttr "joint_on_vertex_018.wm" "skinCluster1.ma[4]";
connectAttr "joint_on_vertex_017.wm" "skinCluster1.ma[5]";
connectAttr "joint_on_vertex_016.wm" "skinCluster1.ma[6]";
connectAttr "joint_on_vertex_015.wm" "skinCluster1.ma[7]";
connectAttr "joint_on_vertex_014.wm" "skinCluster1.ma[8]";
connectAttr "joint_on_vertex_013.wm" "skinCluster1.ma[9]";
connectAttr "joint_on_vertex_012.wm" "skinCluster1.ma[10]";
connectAttr "joint_on_vertex_011.wm" "skinCluster1.ma[11]";
connectAttr "joint_on_vertex_010.wm" "skinCluster1.ma[12]";
connectAttr "joint_on_vertex_009.wm" "skinCluster1.ma[13]";
connectAttr "joint_on_vertex_008.wm" "skinCluster1.ma[14]";
connectAttr "joint_on_vertex_007.wm" "skinCluster1.ma[15]";
connectAttr "joint_on_vertex_006.wm" "skinCluster1.ma[16]";
connectAttr "joint_on_vertex_005.wm" "skinCluster1.ma[17]";
connectAttr "joint_on_vertex_004.wm" "skinCluster1.ma[18]";
connectAttr "joint_on_vertex_003.wm" "skinCluster1.ma[19]";
connectAttr "joint_on_vertex_002.wm" "skinCluster1.ma[20]";
connectAttr "joint_on_vertex_001.wm" "skinCluster1.ma[21]";
connectAttr "joint_on_vertex_021.wm" "skinCluster1.ma[22]";
connectAttr "joint_on_vertex_022.wm" "skinCluster1.ma[23]";
connectAttr "joint_on_vertex_023.wm" "skinCluster1.ma[24]";
connectAttr "joint_on_vertex_024.wm" "skinCluster1.ma[25]";
connectAttr "joint_on_vertex_025.wm" "skinCluster1.ma[26]";
connectAttr "joint_on_vertex_026.wm" "skinCluster1.ma[27]";
connectAttr "joint_on_vertex_027.wm" "skinCluster1.ma[28]";
connectAttr "joint_on_vertex_028.wm" "skinCluster1.ma[29]";
connectAttr "joint_on_vertex_029.wm" "skinCluster1.ma[30]";
connectAttr "joint_on_vertex_030.wm" "skinCluster1.ma[31]";
connectAttr "joint_on_vertex_031.wm" "skinCluster1.ma[32]";
connectAttr "joint_on_vertex_032.wm" "skinCluster1.ma[33]";
connectAttr "joint_on_vertex_033.wm" "skinCluster1.ma[34]";
connectAttr "joint_on_vertex_034.wm" "skinCluster1.ma[35]";
connectAttr "joint_on_vertex_035.wm" "skinCluster1.ma[36]";
connectAttr "joint_on_vertex_036.wm" "skinCluster1.ma[37]";
connectAttr "Root.liw" "skinCluster1.lw[0]";
connectAttr "Main.liw" "skinCluster1.lw[1]";
connectAttr "joint_on_vertex_020.liw" "skinCluster1.lw[2]";
connectAttr "joint_on_vertex_019.liw" "skinCluster1.lw[3]";
connectAttr "joint_on_vertex_018.liw" "skinCluster1.lw[4]";
connectAttr "joint_on_vertex_017.liw" "skinCluster1.lw[5]";
connectAttr "joint_on_vertex_016.liw" "skinCluster1.lw[6]";
connectAttr "joint_on_vertex_015.liw" "skinCluster1.lw[7]";
connectAttr "joint_on_vertex_014.liw" "skinCluster1.lw[8]";
connectAttr "joint_on_vertex_013.liw" "skinCluster1.lw[9]";
connectAttr "joint_on_vertex_012.liw" "skinCluster1.lw[10]";
connectAttr "joint_on_vertex_011.liw" "skinCluster1.lw[11]";
connectAttr "joint_on_vertex_010.liw" "skinCluster1.lw[12]";
connectAttr "joint_on_vertex_009.liw" "skinCluster1.lw[13]";
connectAttr "joint_on_vertex_008.liw" "skinCluster1.lw[14]";
connectAttr "joint_on_vertex_007.liw" "skinCluster1.lw[15]";
connectAttr "joint_on_vertex_006.liw" "skinCluster1.lw[16]";
connectAttr "joint_on_vertex_005.liw" "skinCluster1.lw[17]";
connectAttr "joint_on_vertex_004.liw" "skinCluster1.lw[18]";
connectAttr "joint_on_vertex_003.liw" "skinCluster1.lw[19]";
connectAttr "joint_on_vertex_002.liw" "skinCluster1.lw[20]";
connectAttr "joint_on_vertex_001.liw" "skinCluster1.lw[21]";
connectAttr "joint_on_vertex_021.liw" "skinCluster1.lw[22]";
connectAttr "joint_on_vertex_022.liw" "skinCluster1.lw[23]";
connectAttr "joint_on_vertex_023.liw" "skinCluster1.lw[24]";
connectAttr "joint_on_vertex_024.liw" "skinCluster1.lw[25]";
connectAttr "joint_on_vertex_025.liw" "skinCluster1.lw[26]";
connectAttr "joint_on_vertex_026.liw" "skinCluster1.lw[27]";
connectAttr "joint_on_vertex_027.liw" "skinCluster1.lw[28]";
connectAttr "joint_on_vertex_028.liw" "skinCluster1.lw[29]";
connectAttr "joint_on_vertex_029.liw" "skinCluster1.lw[30]";
connectAttr "joint_on_vertex_030.liw" "skinCluster1.lw[31]";
connectAttr "joint_on_vertex_031.liw" "skinCluster1.lw[32]";
connectAttr "joint_on_vertex_032.liw" "skinCluster1.lw[33]";
connectAttr "joint_on_vertex_033.liw" "skinCluster1.lw[34]";
connectAttr "joint_on_vertex_034.liw" "skinCluster1.lw[35]";
connectAttr "joint_on_vertex_035.liw" "skinCluster1.lw[36]";
connectAttr "joint_on_vertex_036.liw" "skinCluster1.lw[37]";
connectAttr "Root.obcc" "skinCluster1.ifcl[0]";
connectAttr "Main.obcc" "skinCluster1.ifcl[1]";
connectAttr "joint_on_vertex_020.obcc" "skinCluster1.ifcl[2]";
connectAttr "joint_on_vertex_019.obcc" "skinCluster1.ifcl[3]";
connectAttr "joint_on_vertex_018.obcc" "skinCluster1.ifcl[4]";
connectAttr "joint_on_vertex_017.obcc" "skinCluster1.ifcl[5]";
connectAttr "joint_on_vertex_016.obcc" "skinCluster1.ifcl[6]";
connectAttr "joint_on_vertex_015.obcc" "skinCluster1.ifcl[7]";
connectAttr "joint_on_vertex_014.obcc" "skinCluster1.ifcl[8]";
connectAttr "joint_on_vertex_013.obcc" "skinCluster1.ifcl[9]";
connectAttr "joint_on_vertex_012.obcc" "skinCluster1.ifcl[10]";
connectAttr "joint_on_vertex_011.obcc" "skinCluster1.ifcl[11]";
connectAttr "joint_on_vertex_010.obcc" "skinCluster1.ifcl[12]";
connectAttr "joint_on_vertex_009.obcc" "skinCluster1.ifcl[13]";
connectAttr "joint_on_vertex_008.obcc" "skinCluster1.ifcl[14]";
connectAttr "joint_on_vertex_007.obcc" "skinCluster1.ifcl[15]";
connectAttr "joint_on_vertex_006.obcc" "skinCluster1.ifcl[16]";
connectAttr "joint_on_vertex_005.obcc" "skinCluster1.ifcl[17]";
connectAttr "joint_on_vertex_004.obcc" "skinCluster1.ifcl[18]";
connectAttr "joint_on_vertex_003.obcc" "skinCluster1.ifcl[19]";
connectAttr "joint_on_vertex_002.obcc" "skinCluster1.ifcl[20]";
connectAttr "joint_on_vertex_001.obcc" "skinCluster1.ifcl[21]";
connectAttr "joint_on_vertex_021.obcc" "skinCluster1.ifcl[22]";
connectAttr "joint_on_vertex_022.obcc" "skinCluster1.ifcl[23]";
connectAttr "joint_on_vertex_023.obcc" "skinCluster1.ifcl[24]";
connectAttr "joint_on_vertex_024.obcc" "skinCluster1.ifcl[25]";
connectAttr "joint_on_vertex_025.obcc" "skinCluster1.ifcl[26]";
connectAttr "joint_on_vertex_026.obcc" "skinCluster1.ifcl[27]";
connectAttr "joint_on_vertex_027.obcc" "skinCluster1.ifcl[28]";
connectAttr "joint_on_vertex_028.obcc" "skinCluster1.ifcl[29]";
connectAttr "joint_on_vertex_029.obcc" "skinCluster1.ifcl[30]";
connectAttr "joint_on_vertex_030.obcc" "skinCluster1.ifcl[31]";
connectAttr "joint_on_vertex_031.obcc" "skinCluster1.ifcl[32]";
connectAttr "joint_on_vertex_032.obcc" "skinCluster1.ifcl[33]";
connectAttr "joint_on_vertex_033.obcc" "skinCluster1.ifcl[34]";
connectAttr "joint_on_vertex_034.obcc" "skinCluster1.ifcl[35]";
connectAttr "joint_on_vertex_035.obcc" "skinCluster1.ifcl[36]";
connectAttr "joint_on_vertex_036.obcc" "skinCluster1.ifcl[37]";
connectAttr "Root.msg" "bindPose1.m[1]";
connectAttr "Main.msg" "bindPose1.m[2]";
connectAttr "joint_on_vertex_020.msg" "bindPose1.m[3]";
connectAttr "joint_on_vertex_019.msg" "bindPose1.m[4]";
connectAttr "joint_on_vertex_018.msg" "bindPose1.m[5]";
connectAttr "joint_on_vertex_017.msg" "bindPose1.m[6]";
connectAttr "joint_on_vertex_016.msg" "bindPose1.m[7]";
connectAttr "joint_on_vertex_015.msg" "bindPose1.m[8]";
connectAttr "joint_on_vertex_014.msg" "bindPose1.m[9]";
connectAttr "joint_on_vertex_013.msg" "bindPose1.m[10]";
connectAttr "joint_on_vertex_012.msg" "bindPose1.m[11]";
connectAttr "joint_on_vertex_011.msg" "bindPose1.m[12]";
connectAttr "joint_on_vertex_010.msg" "bindPose1.m[13]";
connectAttr "joint_on_vertex_009.msg" "bindPose1.m[14]";
connectAttr "joint_on_vertex_008.msg" "bindPose1.m[15]";
connectAttr "joint_on_vertex_007.msg" "bindPose1.m[16]";
connectAttr "joint_on_vertex_006.msg" "bindPose1.m[17]";
connectAttr "joint_on_vertex_005.msg" "bindPose1.m[18]";
connectAttr "joint_on_vertex_004.msg" "bindPose1.m[19]";
connectAttr "joint_on_vertex_003.msg" "bindPose1.m[20]";
connectAttr "joint_on_vertex_002.msg" "bindPose1.m[21]";
connectAttr "joint_on_vertex_001.msg" "bindPose1.m[22]";
connectAttr "joint_on_vertex_021.msg" "bindPose1.m[23]";
connectAttr "joint_on_vertex_022.msg" "bindPose1.m[24]";
connectAttr "joint_on_vertex_023.msg" "bindPose1.m[25]";
connectAttr "joint_on_vertex_024.msg" "bindPose1.m[26]";
connectAttr "joint_on_vertex_025.msg" "bindPose1.m[27]";
connectAttr "joint_on_vertex_026.msg" "bindPose1.m[28]";
connectAttr "joint_on_vertex_027.msg" "bindPose1.m[29]";
connectAttr "joint_on_vertex_028.msg" "bindPose1.m[30]";
connectAttr "joint_on_vertex_029.msg" "bindPose1.m[31]";
connectAttr "joint_on_vertex_030.msg" "bindPose1.m[32]";
connectAttr "joint_on_vertex_031.msg" "bindPose1.m[33]";
connectAttr "joint_on_vertex_032.msg" "bindPose1.m[34]";
connectAttr "joint_on_vertex_033.msg" "bindPose1.m[35]";
connectAttr "joint_on_vertex_034.msg" "bindPose1.m[36]";
connectAttr "joint_on_vertex_035.msg" "bindPose1.m[37]";
connectAttr "joint_on_vertex_036.msg" "bindPose1.m[38]";
connectAttr "bindPose1.w" "bindPose1.p[0]";
connectAttr "bindPose1.m[0]" "bindPose1.p[1]";
connectAttr "bindPose1.m[1]" "bindPose1.p[2]";
connectAttr "bindPose1.m[2]" "bindPose1.p[3]";
connectAttr "bindPose1.m[2]" "bindPose1.p[4]";
connectAttr "bindPose1.m[2]" "bindPose1.p[5]";
connectAttr "bindPose1.m[2]" "bindPose1.p[6]";
connectAttr "bindPose1.m[2]" "bindPose1.p[7]";
connectAttr "bindPose1.m[2]" "bindPose1.p[8]";
connectAttr "bindPose1.m[2]" "bindPose1.p[9]";
connectAttr "bindPose1.m[2]" "bindPose1.p[10]";
connectAttr "bindPose1.m[2]" "bindPose1.p[11]";
connectAttr "bindPose1.m[2]" "bindPose1.p[12]";
connectAttr "bindPose1.m[2]" "bindPose1.p[13]";
connectAttr "bindPose1.m[2]" "bindPose1.p[14]";
connectAttr "bindPose1.m[2]" "bindPose1.p[15]";
connectAttr "bindPose1.m[2]" "bindPose1.p[16]";
connectAttr "bindPose1.m[2]" "bindPose1.p[17]";
connectAttr "bindPose1.m[2]" "bindPose1.p[18]";
connectAttr "bindPose1.m[2]" "bindPose1.p[19]";
connectAttr "bindPose1.m[2]" "bindPose1.p[20]";
connectAttr "bindPose1.m[2]" "bindPose1.p[21]";
connectAttr "bindPose1.m[2]" "bindPose1.p[22]";
connectAttr "bindPose1.m[2]" "bindPose1.p[23]";
connectAttr "bindPose1.m[2]" "bindPose1.p[24]";
connectAttr "bindPose1.m[2]" "bindPose1.p[25]";
connectAttr "bindPose1.m[2]" "bindPose1.p[26]";
connectAttr "bindPose1.m[2]" "bindPose1.p[27]";
connectAttr "bindPose1.m[2]" "bindPose1.p[28]";
connectAttr "bindPose1.m[2]" "bindPose1.p[29]";
connectAttr "bindPose1.m[2]" "bindPose1.p[30]";
connectAttr "bindPose1.m[2]" "bindPose1.p[31]";
connectAttr "bindPose1.m[2]" "bindPose1.p[32]";
connectAttr "bindPose1.m[2]" "bindPose1.p[33]";
connectAttr "bindPose1.m[2]" "bindPose1.p[34]";
connectAttr "bindPose1.m[2]" "bindPose1.p[35]";
connectAttr "bindPose1.m[2]" "bindPose1.p[36]";
connectAttr "bindPose1.m[2]" "bindPose1.p[37]";
connectAttr "bindPose1.m[2]" "bindPose1.p[38]";
connectAttr "Root.bps" "bindPose1.wm[1]";
connectAttr "Main.bps" "bindPose1.wm[2]";
connectAttr "joint_on_vertex_020.bps" "bindPose1.wm[3]";
connectAttr "joint_on_vertex_019.bps" "bindPose1.wm[4]";
connectAttr "joint_on_vertex_018.bps" "bindPose1.wm[5]";
connectAttr "joint_on_vertex_017.bps" "bindPose1.wm[6]";
connectAttr "joint_on_vertex_016.bps" "bindPose1.wm[7]";
connectAttr "joint_on_vertex_015.bps" "bindPose1.wm[8]";
connectAttr "joint_on_vertex_014.bps" "bindPose1.wm[9]";
connectAttr "joint_on_vertex_013.bps" "bindPose1.wm[10]";
connectAttr "joint_on_vertex_012.bps" "bindPose1.wm[11]";
connectAttr "joint_on_vertex_011.bps" "bindPose1.wm[12]";
connectAttr "joint_on_vertex_010.bps" "bindPose1.wm[13]";
connectAttr "joint_on_vertex_009.bps" "bindPose1.wm[14]";
connectAttr "joint_on_vertex_008.bps" "bindPose1.wm[15]";
connectAttr "joint_on_vertex_007.bps" "bindPose1.wm[16]";
connectAttr "joint_on_vertex_006.bps" "bindPose1.wm[17]";
connectAttr "joint_on_vertex_005.bps" "bindPose1.wm[18]";
connectAttr "joint_on_vertex_004.bps" "bindPose1.wm[19]";
connectAttr "joint_on_vertex_003.bps" "bindPose1.wm[20]";
connectAttr "joint_on_vertex_002.bps" "bindPose1.wm[21]";
connectAttr "joint_on_vertex_001.bps" "bindPose1.wm[22]";
connectAttr "joint_on_vertex_021.bps" "bindPose1.wm[23]";
connectAttr "joint_on_vertex_022.bps" "bindPose1.wm[24]";
connectAttr "joint_on_vertex_023.bps" "bindPose1.wm[25]";
connectAttr "joint_on_vertex_024.bps" "bindPose1.wm[26]";
connectAttr "joint_on_vertex_025.bps" "bindPose1.wm[27]";
connectAttr "joint_on_vertex_026.bps" "bindPose1.wm[28]";
connectAttr "joint_on_vertex_027.bps" "bindPose1.wm[29]";
connectAttr "joint_on_vertex_028.bps" "bindPose1.wm[30]";
connectAttr "joint_on_vertex_029.bps" "bindPose1.wm[31]";
connectAttr "joint_on_vertex_030.bps" "bindPose1.wm[32]";
connectAttr "joint_on_vertex_031.bps" "bindPose1.wm[33]";
connectAttr "joint_on_vertex_032.bps" "bindPose1.wm[34]";
connectAttr "joint_on_vertex_033.bps" "bindPose1.wm[35]";
connectAttr "joint_on_vertex_034.bps" "bindPose1.wm[36]";
connectAttr "joint_on_vertex_035.bps" "bindPose1.wm[37]";
connectAttr "joint_on_vertex_036.bps" "bindPose1.wm[38]";
connectAttr "TechLimbShield_MatSG.msg" "materialInfo2.sg";
connectAttr "TechLimbShield_Mat.oc" "TechLimbShield_MatSG.ss";
connectAttr "TechLimbShieldMeshShape.iog" "TechLimbShield_MatSG.dsm" -na;
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" "TechLimbShield_MatSG.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" "TechLimbShield_MatSG.message" ":defaultLightSet.message";
connectAttr "TechLimbShield_MatSG.pa" ":renderPartition.st" -na;
connectAttr "TechLimbShield_Mat.msg" ":defaultShaderList1.s" -na;
// End of Tech_Limb_Shield.ma
