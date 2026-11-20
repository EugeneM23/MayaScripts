//Maya ASCII 2027 scene
//Name: MainHero_Cape.ma
//Last modified: Fri, Nov 20, 2026 05:41:25 PM
//Codeset: 1252
requires maya "2027";
currentUnit -l centimeter -a degree -t ntsc;
fileInfo "application" "maya";
fileInfo "product" "Maya 2027";
fileInfo "version" "2027";
fileInfo "cutIdentifier" "202607171511-52c21617ee";
fileInfo "osv" "Windows 11 Home v2009 (Build: 26200)";
fileInfo "UUID" "71DF4079-471D-ED8C-5B64-CE80E624B283";
createNode transform -s -n "persp";
	rename -uid "51621BD9-4E21-F04F-8085-A88E7600384E";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 28 21 28 ;
	setAttr ".r" -type "double3" -27.938352729602379 44.999999999999972 -5.172681101354183e-14 ;
createNode camera -s -n "perspShape" -p "persp";
	rename -uid "3CE7466A-4356-F2DC-7DA4-DEAAE3A6C74D";
	setAttr -k off ".v" no;
	setAttr ".fl" 34.999999999999993;
	setAttr ".coi" 44.82186966202994;
	setAttr ".imn" -type "string" "persp";
	setAttr ".den" -type "string" "persp_depth";
	setAttr ".man" -type "string" "persp_mask";
	setAttr ".hc" -type "string" "viewSet -p %camera";
createNode transform -s -n "top";
	rename -uid "0858AEA3-46DE-BF8C-8FF8-87B9AFE3DA65";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 1000.1 0 ;
	setAttr ".r" -type "double3" -90 0 0 ;
createNode camera -s -n "topShape" -p "top";
	rename -uid "97B1BF85-42D9-9F90-96FC-3F8BA7BA4132";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "top";
	setAttr ".den" -type "string" "top_depth";
	setAttr ".man" -type "string" "top_mask";
	setAttr ".hc" -type "string" "viewSet -t %camera";
	setAttr ".o" yes;
createNode transform -s -n "front";
	rename -uid "865F91F3-439F-B9B1-8461-25A9649353F2";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 0 1000.1 ;
createNode camera -s -n "frontShape" -p "front";
	rename -uid "EEA95135-4258-66C3-B942-859839738C7A";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "front";
	setAttr ".den" -type "string" "front_depth";
	setAttr ".man" -type "string" "front_mask";
	setAttr ".hc" -type "string" "viewSet -f %camera";
	setAttr ".o" yes;
createNode transform -s -n "side";
	rename -uid "2CD2B3BF-446A-7061-26A5-1EABB72675C3";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 1000.1 0 0 ;
	setAttr ".r" -type "double3" 0 90 0 ;
createNode camera -s -n "sideShape" -p "side";
	rename -uid "5B67EB37-48C8-22A2-FEEB-DE82BE8657E4";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "side";
	setAttr ".den" -type "string" "side_depth";
	setAttr ".man" -type "string" "side_mask";
	setAttr ".hc" -type "string" "viewSet -s %camera";
	setAttr ".o" yes;
createNode joint -n "root";
	rename -uid "E1FB2DF5-4FEB-CB23-FA2E-C5B5D52A1D91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".jo" -type "double3" -90 0 0 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 2;
createNode joint -n "pelvis" -p "root";
	rename -uid "04056686-480E-0E1D-B5CB-DDAB7335F57A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.4314998759166215e-17 -2.2808661460876465 95.896781921386719 ;
	setAttr ".r" -type "double3" -90 -86.366893050032431 90 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99799027986901867 -0.063367194090933054 0 0 -0.063367194090933054 -0.99799027986901856 0
		 -1 0 0 0 -3.4314998759166215e-17 95.896781921386719 2.2808661460876465 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_01" -p "pelvis";
	rename -uid "8BBEF5BA-4A92-15C8-8DA0-008BEEA645CE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.6770534515381001 7.1054273576010019e-15 -4.6633694517662434e-16 ;
	setAttr ".r" -type "double3" -4.8675251569720316e-17 2.1703504497372443e-16 -14.457321828304911 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.98220797016103356 0.18779644126591361 0 0 0.18779644126591366 -0.98220797016103356 0
		 -1 0 0 0 4.3202194641745812e-16 99.566445524580573 2.0478615863412895 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_02" -p "spine_01";
	rename -uid "A8371707-4A55-11B9-13B8-55AB8A81AC9F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 6.7950572967529155 1.7763568394002505e-14 1.8559423937125809e-16 ;
	setAttr ".r" -type "double3" -8.7467656525930775e-18 2.1960301960102488e-16 3.4644695084247532 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99176140629857157 0.12809884065314411 0 0 0.12809884065314417 -0.99176140629857157 0
		 -1 0 0 0 2.4642770704620003e-16 106.24060495915218 3.3239491648694486 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_03" -p "spine_02";
	rename -uid "0E205E4E-4FD7-D3C6-7E1F-7CBA500B8F0B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 7.2382278442382812 -1.9539925233402755e-14 1.2292061026364971e-16 ;
	setAttr ".r" -type "double3" 7.7116540289099159e-17 2.1691490646910566e-16 10.946079405533537 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0 0.99804167658749543 -0.062552472328609832 0 0 -0.062552472328609776 -0.99804167658749543 0
		 -1 0 0 0 1.2350709678255032e-16 113.41919998506341 4.2511577600996988 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_04" -p "spine_03";
	rename -uid "F38A1D48-4EAC-673A-3838-4CAB83FA32AD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 8.5238933563232422 -7.1054273576010019e-15 2.5229931328786502e-16 ;
	setAttr ".r" -type "double3" 0.00044952872062768446 -2.3921337171503338e-12 5.8669839318741532 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 5.2939559203393771e-23 0.98641974755132855 -0.16424396987644224 0
		 -7.8457562571503496e-06 -0.16424396987138709 -0.98641974752096839 0 -0.99999999996922206 1.2886181543573101e-06 7.7392089065275053e-06 0
		 -1.287922165053147e-16 121.92640080146128 3.7179671567962753 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "spine_05" -p "spine_04";
	rename -uid "C8734AB2-4B19-DA8F-9EF6-9EB582E1D962";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 19.439800262451158 -1.7817309228007616e-07 8.1130192624775943e-13 ;
	setAttr ".r" -type "double3" -0.0004494978431558535 5.3458782907563942e-06 0.68138935939447021 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -1.8369095114106268e-13 0.98439676970875745 -0.17596306370077883 0
		 1.5897534121574511e-11 -0.17596306370077877 -0.98439676970875722 0 -1 -2.9782035875482524e-12 -1.561715840808363e-11 0
		 5.8647193620207408e-13 141.10220369806046 0.52509736383965011 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "neck_01" -p "spine_05";
	rename -uid "22ADCBC7-4099-1E13-CD8B-FE93A6487F17";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 11.887765884399442 1.0658141036401503e-14 1.5994409772213136e-15 ;
	setAttr ".r" -type "double3" -5.3236884653331409e-16 4.0208541712268971e-15 -23.928404052334628 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -6.6158600092334618e-12 0.9711605157890677 0.23842661884175748 0
		 1.4456684607833927e-11 0.23842661884175759 -0.97116051578906759 0 -1 -2.9782035875482524e-12 -1.561715840808363e-11 0
		 -1.5988025270225873e-12 152.80448203371725 -1.5667103417368851 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "neck_02" -p "neck_01";
	rename -uid "3AAB785F-4D3C-88CA-4663-DB86DC9CC9A1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.1102595329284384 -6.3948846218409017e-14 -4.1190754660973504e-14 ;
	setAttr ".r" -type "double3" -9.7964785669111379e-05 1.7913575251998921e-14 1.9135286365136508 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -6.1294451692525523e-12 0.97858030038111232 0.20586547963661239 0
		 1.7098227304699773e-06 0.20586547963631158 -0.9785803003796818 0 -0.99999999999853828 3.5198747834749016e-07 -1.6732001030229289e-06 0
		 -3.5366373453067859e-11 157.76736431753201 -0.34828843989683644 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "head" -p "neck_02";
	rename -uid "BFCC0929-4B6E-EF0F-2BBA-47A8FA211A91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9129710197448446 -4.9737991503207013e-14 2.0180004314720307e-14 ;
	setAttr ".r" -type "double3" 9.5867333842692594e-05 -2.0167398412977789e-05 11.88016967271599 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 2.0731684602442676e-14 0.99999999999999967 -2.7642915900707275e-08 0
		 -5.2736971644069353e-13 -2.764291584511913e-08 -1 0 -1 2.0731699954914845e-14 5.2736972046410003e-13 0
		 -6.5500340026078519e-11 162.57510097379762 0.66312269552376124 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "clavicle_l" -p "spine_05";
	rename -uid "67BEFB0F-4545-B0F3-EA12-4D93404F5F47";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.5162687301636311 1.3147660493850672 -1.4279042482376099 ;
	setAttr ".r" -type "double3" 163.26358510455574 80.83122589010857 153.12438365112951 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.98722325285369927 -0.15258975017460921 -0.04589789937036267 0
		 -0.045885930500282501 0.0036018072449419511 -0.99894019258747135 0 0.15259334981277772 0.98828305415312057 -0.0034459348070640019 0
		 1.4279042482580846 146.30105055478367 -1.7398136340318517 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_l" -p "clavicle_l";
	rename -uid "C708BA75-4C6C-D0B4-7C32-1286097F36E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 17.809522628784187 1.6431300764452317e-14 5.6843418860808015e-14 ;
	setAttr ".r" -type "double3" -4.3373452619178403 46.029604216550808 -4.3585186559704923 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970603881 -0.81709064454000013 0.023413781773248588 0
		 -0.032592100671480363 -0.051578494511193465 -0.99813697150129621 0 0.81677602899787549 0.57419729841681155 -0.056341644857918607 0
		 19.00987910961798 143.58349994612851 -2.5572333114820021 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_l" -p "upperarm_l";
	rename -uid "1F9B3AB2-47B5-1BD7-0599-EBA3A7A55210";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 27.771139144897504 1.3322676295501878e-14 -1.1368683772161603e-13 ;
	setAttr ".r" -type "double3" -1.1529510720305249e-14 3.5781240166464568e-15 -38.978821942625935 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.46829763500528582 -0.60274413765566637 0.64606255855774819 0
		 0.33700777958812461 -0.55407307010227569 -0.76120220013116158 0 0.81677602899787549 0.57419729841681155 -0.056341644857918607 0
		 35.006987526056307 120.89196196261412 -1.9070059199488574 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_02_l" -p "lowerarm_l";
	rename -uid "E08A9CA0-4CDC-5BA6-1DDE-CEB545F4290E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 9.0836915969848633 -7.1054273576010019e-14 9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" 1.2856768460267047 -1.7275331230962776 1.9858280815512741 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409945495245201 -0.60398945624054479 0.61731716019149607 0
		 0.33849062611899527 -0.51942160302091644 -0.78461792889581128 0 0.79454882514934966 0.60448154236951845 -0.057395377761239416 0
		 39.260858818041761 115.41682010425956 3.96162711434875 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_01_l" -p "lowerarm_l";
	rename -uid "6173084E-480E-C038-0FE7-13B6B461187B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.167383193969734 -2.8421709430404007e-14 7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" 1.2856768693497316 -1.7275255464774961 1.9858281662294717 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409934937944101 -0.60398953540120925 0.61731716895049749 0
		 0.3384906272290289 -0.51942160364797829 -0.7846179280018154 0 0.79454889165697262 0.60448146273446102 -0.057395295774846602 0
		 43.514730110027159 109.94167824590484 9.8302601486462819 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "hand_l" -p "lowerarm_l";
	rename -uid "774D05BE-4BCD-BE4B-C5F9-C98EDA56CF52";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 27.251073837280284 -2.1316282072803006e-14 9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" -67.770758746900071 1.4734707800079263 1.8489162697849526 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000011 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776606561811412 -0.63486683690404522 0.62241009677540249 0
		 -0.6455090443714524 -0.71872771411568381 -0.25835740089399245 0 0.61136593199422506 -0.28350409584606823 -0.73882144313449338 0
		 47.768600955409156 104.46653696237179 15.698892566810567 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_metacarpal_l" -p "hand_l";
	rename -uid "50C416CE-4E92-521E-5C07-388445757BB1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3758335113525533 -0.75357073545451669 -0.18286436796188354 ;
	setAttr ".r" -type "double3" -4.2725003027381687 -0.13075114456698561 -2.3183915821069538 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999967 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.48489773769626732 -0.60591821332048423 0.63066417588408685 0
		 -0.67018644860059928 -0.72073617183479377 -0.17717080662751097 0 0.56189350244433178 -0.33675286097587692 -0.7555615147262349 0
		 49.688582660644784 102.91678718852391 18.129840122146437 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_01_l" -p "middle_metacarpal_l";
	rename -uid "0898D6D8-403F-0FB5-3F5C-A1B5562346DF";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 6.0982089042663432 5.6843418860808015e-14 1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 6.3611093629270351e-15 -3.1805546814635148e-15 31.57268201739824 ;
	setAttr ".s" -type "double3" 1.0000000000000009 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.062225503872753773 -0.89359104695641389 0.44454811603146327 0
		 -0.8248658548992216 -0.29680389388264872 -0.48114838667242188 0 0.561893502444332 -0.33675286097587709 -0.75556151472623523 0
		 52.645590362322736 99.221771344795741 21.975762015124548 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_02_l" -p "middle_01_l";
	rename -uid "B789626D-4CE7-3848-7020-E38C339FC0E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.1690001487731934 -1.4210854715202004e-14 4.2632564145606011e-14 ;
	setAttr ".r" -type "double3" 6.3611093629270335e-15 1.4312496066585827e-14 20.769210477739517 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23431932551154863 -0.94077026842430223 0.24504235499333737 0
		 -0.79332852312434521 0.039354957418722358 -0.60752040436837751 0 0.561893502444332 -0.33675286097587709 -0.75556151472623523 0
		 52.967234001098525 94.602799090135633 24.273631293028 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_03_l" -p "middle_02_l";
	rename -uid "F4EB25C8-463F-D9E1-3EA0-BDA730D451F1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.4739999771118164 4.2632564145606011e-14 0 ;
	setAttr ".r" -type "double3" 2.544443745170814e-14 5.5659706925611543e-15 9.9999999709533771 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.36851954040065671 -0.91964393761217478 0.13582480022464374 0
		 -0.74058695657817952 0.20212010943431011 -0.6408419626620383 0 0.56189350244433178 -0.33675286097587698 -0.75556151472623501 0
		 52.387527995146066 92.275333467586435 24.879866073672915 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_metacarpal_l" -p "hand_l";
	rename -uid "AA09A4C3-4C81-5AB1-7A91-EC855B45D24E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3143784999847554 -0.30591726303099165 2.3911108970642037 ;
	setAttr ".r" -type "double3" -27.769049129171513 -19.527703069996932 11.850627289629655 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50165929984922653 -0.81946977563034828 0.27714118009262256 0
		 -0.86150484141863282 -0.50229885137241914 0.074197520997708155 0 0.078405070544199928 -0.27598034484052558 -0.95796006919634324 0
		 50.945127063517511 101.90432945001062 16.074227195038095 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_01_l" -p "pinky_metacarpal_l";
	rename -uid "5200829B-4A82-EA71-D2EC-46B78D79507E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9575676918029927 -0.14312039315700531 -0.19884027540683746 ;
	setAttr ".r" -type "double3" 10.491640062438089 0.60504264270137542 14.833680882858816 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.2635405017513856 -0.91778928814692995 0.29700038131184431 0
		 -0.93037057822145863 -0.32317414573818048 -0.17311573789308446 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 53.539845826532741 97.968517782802252 17.628035221144721 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_02_l" -p "pinky_01_l";
	rename -uid "2598D9BD-4940-0674-6D05-F688AEEB5359";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.8159999847411825 1.8474111129762605e-13 6.3948846218409017e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635168e-15 0 21.28699904924385 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.092201469831925953 -0.9724969364063768 0.21388921815053269 0
		 -0.96257046383334244 0.032068903802027982 -0.26912764176985227 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 54.545516377194559 94.466233873237869 18.761388671698754 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_03_l" -p "pinky_02_l";
	rename -uid "1D392A30-424E-B41A-7A1B-6D9114BD6FCC";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.0399999618530416 7.1054273576010019e-15 1.7763568394002505e-14 ;
	setAttr ".r" -type "double3" 0 -3.1805546814635168e-15 4.9170000470223698 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.17436652109979212 -0.96616935149144467 0.19003447202589094 0
		 -0.9511252941663676 0.11530607160706441 -0.28647021598673916 0 0.25486661436229252 -0.23069740806768885 -0.93905362721963437 0
		 54.357425382254632 92.482340160066656 19.197722668566598 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_metacarpal_l" -p "hand_l";
	rename -uid "8BABCB75-4646-EB42-7505-88BD8DD45435";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.3743038177490234 -0.54251688718794355 1.0917565822601283 ;
	setAttr ".r" -type "double3" -13.299834889366425 -11.809318654920906 -1.5945633604277318 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999989 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.59060503118117402 -0.65963271076520424 0.46483371653961758 0
		 -0.73083333884862711 -0.68147046384688714 -0.038479055753444874 0 0.34215249227625494 -0.31699005314497924 -0.88456146097164412 0
		 50.330905076088669 102.40470783030432 17.132643411823313 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_01_l" -p "ring_metacarpal_l";
	rename -uid "407F76B5-4653-BF41-6B67-FCAE06E76E7E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.6455168724060023 -0.041624534875168706 -0.020689174532893873 ;
	setAttr ".r" -type "double3" 6.3958444445851228 -0.11693801365857265 29.414482479749061 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.15623819408419617 -0.90993079452509829 0.38420772491483429 0
		 -0.88283473502988641 -0.30308700145347278 -0.35880510054158071 0 0.44293617749515529 -0.28313286408480798 -0.85067227763758335 0
		 53.688517489721136 98.715664385711946 19.776772520660199 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_02_l" -p "ring_01_l";
	rename -uid "74AA1E84-4E03-592A-0BE9-42BE3B5E5362";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.9770002365112447 -7.1054273576010019e-14 -9.5923269327613525e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635176e-15 7.9513867036587888e-15 18.963999541971795 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.13914028536722992 -0.95903783110600926 0.2467517365600666 0
		 -0.88569042201770853 0.0090675124822772735 -0.4641877384889419 0 0.4429361774951554 -0.28313286408480803 -0.85067227763758357 0
		 54.46611501863029 94.186938606151713 21.688974458430884 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_03_l" -p "ring_02_l";
	rename -uid "127A32B1-4CB7-097A-354D-13A4E982158D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.265000104904189 3.5527136788005009e-14 1.5987211554602254e-13 ;
	setAttr ".r" -type "double3" 0 2.2263882770244614e-14 9.1679997480249913 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.27847973581337387 -0.94534178719106776 0.16964062641865238 0
		 -0.85220688767886321 0.16175502052651367 -0.49757284283527181 0 0.4429361774951554 -0.28313286408480803 -0.85067227763758357 0
		 54.150962257677158 92.014717818089466 22.247867167624573 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_01_l" -p "hand_l";
	rename -uid "2459D9A1-4241-8534-D5CF-9C92A7C298B5";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 1.992446541786201 1.3566048145294474 -2.5815360546112114 ;
	setAttr ".r" -type "double3" 73.564463907750024 39.90417842702314 20.508675504416569 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 0.99999999999999867 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23677732947120186 -0.46744570505554739 0.85172237793403616 0
		 0.35804510680805463 -0.85693276787306882 -0.37076937958279521 0 0.90318336883453154 0.21716524623089306 0.37026889970693044 0
		 46.226711496376346 102.95844529643908 18.495816711153008 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_02_l" -p "thumb_01_l";
	rename -uid "E1EDD2A9-4EE9-5058-C2C1-C8B67C4C0171";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.3779997825622416 9.9475983006414026e-14 -7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" 3.5306280002014567 -1.9322904957701326 23.246005781061328 ;
	setAttr ".s" -type "double3" 1 1.0000000000000004 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.045744985004836883 -0.75995290887963518 0.64836638764844179 0
		 0.47737462531297947 -0.58677024939719435 -0.65407502744688883 0 0.87750832671502266 0.27959300904660811 0.38962403139188362 0
		 45.190100399435728 100.91196810134613 22.22465709655155 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_03_l" -p "thumb_02_l";
	rename -uid "9EB8734A-4DA2-9D71-28F5-82BE6A786C05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.0859999656677246 4.2632564145606011e-14 7.1054273576010019e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635176e-15 -3.1805546814635164e-15 9.9999999709533807 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.037845217613482196 -0.8502991008797891 0.5249373091587336 0
		 0.47806576540219692 -0.44589145353469928 -0.75672579949088947 0 0.87750832671502255 0.27959300904660805 0.38962403139188356 0
		 45.048931377281413 98.566753450634479 24.225515746574747 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_metacarpal_l" -p "hand_l";
	rename -uid "26B00FE3-474F-4ED8-974C-6DBD987F02A1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 3.4445061683654821 -0.3846808075904562 -2.3793244361877459 ;
	setAttr ".r" -type "double3" 3.2877464546581483 7.3255016683865124 -0.60616237917610527 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.38282471691666847 -0.58595958989602792 0.71421046976822766 0
		 -0.60140250132809681 -0.74492304281921029 -0.28879870441758848 0 0.70125620675611955 -0.31896868072876305 -0.63757251603262366 0
		 48.139056031148343 103.23076320707465 19.700069031658664 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_01_l" -p "index_metacarpal_l";
	rename -uid "83EB876C-4581-FF38-B6C1-FD921AA83A05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.8770980834960902 0.043181736022219752 0.24087569117545549 ;
	setAttr ".r" -type "double3" 1.2722218725854073e-14 1.2722218725854067e-14 23.372999646513961 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.11282515358796361 -0.8333991415651697 0.54103267512812159 0
		 -0.70392486616390482 -0.45133673853630707 -0.54843863033482487 0 0.70125620675611955 -0.31896868072876305 -0.63757251603262366 0
		 50.531900410692231 99.678022352664797 23.731507464854804 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_02_l" -p "index_01_l";
	rename -uid "D958BC96-43A1-1812-5136-74BE80133B8D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 4.0799999237060547 0 -9.0594198809412774e-14 ;
	setAttr ".r" -type "double3" 3.1805546814635195e-15 9.5416640443905503e-15 14.892568419110976 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.071878640933651761 -0.92140168606419925 0.38190626323167681 0
		 -0.70927652820571307 -0.22198629154117516 -0.66906568653925691 0 0.70125620675611944 -0.318968680728763 -0.63757251603262355 0
		 50.992227028723185 96.277753918662242 25.93892073810008 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_03_l" -p "index_02_l";
	rename -uid "BF63893B-47F7-7BB0-8B59-D2A5ADC46166";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.5950000286102437 7.1054273576010019e-14 -2.1316282072803006e-14 ;
	setAttr ".r" -type "double3" -3.1805546814635187e-15 1.7493050748049344e-14 12.516400997546974 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999933 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.22388412434001692 -0.94761232662415895 0.22783058903152797 0
		 -0.67684239772233667 -0.017025250192035518 -0.73593104942064802 0 0.70125620675611944 -0.318968680728763 -0.63757251603262355 0
		 50.80570195344383 93.886716516964114 26.929967502112678 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "weapon_l" -p "hand_l";
	rename -uid "0A3E0598-4E30-B1A8-8D04-21A8CB58DB5B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 1.1633778810501241 1.3170588016510436 0.51951599121093395 ;
	setAttr ".r" -type "double3" -11.617611580307605 -15.808370734790156 8.5170863439819282 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999978 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.5101570886898299 -0.78377147370740308 0.35417795225288096 0
		 -0.79058848355508882 -0.589491018503433 -0.16574133091613166 0 0.33868804899137267 -0.19545489532450003 -0.92037372266058592 0
		 47.768596880562413 102.63405535367295 15.698889263164309 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_01_l" -p "upperarm_l";
	rename -uid "01545CBE-4AA4-C937-D152-239A3F2A958C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 9.2570457458496378 1.1546319456101628e-14 -9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" 2.6828436514387616e-10 -2.1533312395632254 -0.32660888591551879 ;
	setAttr ".s" -type "double3" 1.0000000000000004 0.99999999999999978 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.60649254765415872 -0.79463176670251345 0.026965626030396716 0
		 -0.029307966917277297 -0.05623537513571026 -0.99798728732310094 0 0.7945488233677932 0.60448154473944693 -0.057395377464279168 0
		 24.342248215531768 136.0196544711159 -2.3404908625237053 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_02_l" -p "upperarm_l";
	rename -uid "FB8F535E-4808-DF94-BAF2-358C2852E834";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 18.514091491699276 8.8817841970012523e-15 -9.9475983006414026e-14 ;
	setAttr ".r" -type "double3" -2.7829853462805776e-15 4.4478069373591348e-15 3.975693351829394e-16 ;
	setAttr ".s" -type "double3" 1.0000000000000004 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970603903 -0.81709064454000047 0.023413781773248599 0
		 -0.032592100671480356 -0.051578494511193458 -0.9981369715012961 0 0.81677602899787571 0.57419729841681166 -0.056341644857918621 0
		 29.674617321445631 128.45580899610337 -2.1237484135654001 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "clavicle_r" -p "spine_05";
	rename -uid "87E969E6-45D3-9DE0-98D7-279443506364";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 5.5162200927734375 1.314811229705807 1.4278726577758791 ;
	setAttr ".r" -type "double3" 163.26358510455586 80.831225890108584 -26.875616348870519 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.98722325285135692 0.15258975018048915 0.045897899401197824 0
		 -0.045885930531461866 -0.003601807245217459 0.99894019258603828 0 0.15259334981855652 -0.98828305415221218 0.0034459348118279862 0
		 -1.4278726577554037 146.30099472621771 -1.739849551054053 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_r" -p "clavicle_r";
	rename -uid "0058AC87-4DAE-67EF-A60F-13B3E8C44FB9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -17.809625625610355 2.8716144648832653e-06 0.00043809693306684494 ;
	setAttr ".r" -type "double3" -4.337345261917843 46.029604216550808 -4.3585186559704807 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970190345 0.8170906445434315 -0.02341378175525494 0
		 -0.032592100702963554 0.051578494510997164 0.99813697150027847 0 0.81677602899953572 -0.574197298411947 0.056341644883428681 0
		 -19.009882481023482 143.58299542707977 -2.5572695781667329 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_r" -p "upperarm_r";
	rename -uid "8FBCC084-4895-1DA5-2DB4-48BC4382CCC3";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -27.770694732666016 -3.4638958368304884e-14 5.6843418860808015e-14 ;
	setAttr ".r" -type "double3" -1.1529510720305249e-14 1.5505204072134644e-14 -38.978821942625942 ;
	setAttr ".s" -type "double3" 1 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.46829763502187488 0.60274413765845714 -0.64606255854312011 0
		 0.33700777956104905 0.55407307010428153 0.76120220014168893 0 0.81677602899953594 -0.57419729841194711 0.056341644883428695 0
		 -35.006734900982885 120.89182056854678 -1.9070525925043142 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_02_r" -p "lowerarm_r";
	rename -uid "17C218AF-40AB-865E-A2AA-32A968CB5CFE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -9.0836620330810547 -1.4210854715202004e-14 -1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 1.285676846026711 -1.7275331230962687 1.9858280815512903 ;
	setAttr ".s" -type "double3" 1 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409945496813557 0.60398945624354872 -0.61731716017574922 0
		 0.33849062609139469 0.51942160302293094 0.78461792890638504 0 0.79454882515115777 -0.60448154236478657 0.057395377786055017 0
		 -39.260592348412757 115.41669652963647 3.9615613415290207 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "lowerarm_twist_01_r" -p "lowerarm_r";
	rename -uid "1FD089A5-4F57-61BE-1C23-C3A879214D4C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -18.167304992675781 -7.1054273576010019e-15 -1.4210854715202004e-14 ;
	setAttr ".r" -type "double3" 1.2856768693497385 -1.7275255464774895 1.9858281662294912 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50409934939512469 0.60398953540421341 -0.61731716893475086 0
		 0.33849062720142825 0.51942160364999246 0.78461792801238917 0 0.79454889165878051 -0.60448146272972902 0.057395295799662197 0
		 -43.51444086377407 109.94158398715824 9.8301629528969965 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "hand_r" -p "lowerarm_r";
	rename -uid "06B77F40-4C21-9A1C-B317-7993B98C14D1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -27.251010894775412 -7.1054273576010019e-15 0 ;
	setAttr ".r" -type "double3" -67.770758746900086 1.4734707800079416 1.8489162697849597 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000007 0.99999999999999956 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776606563377292 0.63486683690677337 -0.62241009676110326 0
		 -0.64550904438380341 0.71872771411183844 0.2583574008738318 0 0.61136593196945999 0.28350409584970843 0.73882144315358966 0
		 -47.768318854961556 104.46643350645415 15.698805229060721 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_metacarpal_r" -p "hand_r";
	rename -uid "C5404CCC-4367-3011-D34B-5293ABAC7D9D";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3758001327514471 0.75400394201277265 0.18280552327632194 ;
	setAttr ".r" -type "double3" -4.2725003027381421 -0.1307511445669825 -2.3183915821069596 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999933 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.48489773771235634 0.60591821332337392 -0.6306641758689403 0
		 -0.67018644861042598 0.72073617183080163 0.17717080660657977 0 0.56189350241872704 0.33675286097922214 0.75556151474378597 0
		 -49.688600895060446 102.91699959841172 18.129800455563196 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_01_r" -p "middle_metacarpal_r";
	rename -uid "B61EFD77-4043-29F9-4F8C-8BAAAB339084";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -6.0983657836914205 -0.0001238507247620646 1.430381864508945e-06 ;
	setAttr ".r" -type "double3" 6.3611093629270351e-15 3.180554681463516e-15 31.572682017398236 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.062225503881316258 0.89359104695678526 -0.44454811602951783 0
		 -0.82486585491601749 0.29680389387773476 0.48114838664665849 0 0.56189350241872726 0.3367528609792223 0.7555615147437863 0
		 -52.645600860515195 99.221799916552953 21.975800424690974 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_02_r" -p "middle_01_r";
	rename -uid "5497A187-41B3-18AE-8799-CC95F46AA277";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.1689915657043315 -7.7438591688405722e-05 -3.7045669152746541e-05 ;
	setAttr ".r" -type "double3" 3.180554681463516e-15 1.4312496066585818e-14 20.769210477739527 ;
	setAttr ".s" -type "double3" 1.0000000000000007 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23431932550949874 0.94077026842290723 -0.24504235500065422 0
		 -0.79332852314308611 -0.039354957423448855 0.60752040434359866 0 0.56189350241872738 0.33675286097922236 0.75556151474378652 0
		 -52.967200904520077 94.602799872333804 24.273600637261946 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "middle_03_r" -p "middle_02_r";
	rename -uid "DC20D660-48A1-E8A9-2B53-7398BCD6D8EA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.4740469455719136 4.577730578603223e-05 3.4385015172944122e-05 ;
	setAttr ".r" -type "double3" 3.1805546814635176e-15 1.033680271475643e-14 9.9999999709533824 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.36851954040189233 0.91964393760998009 -0.13582480023615218 0
		 -0.7405869565969917 -0.20212010943872263 0.64084196263890647 0 0.56189350241872749 0.33675286097922241 0.75556151474378674 0
		 -52.38750088868062 92.27529984094555 24.879900717828534 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_metacarpal_r" -p "hand_r";
	rename -uid "C60C3488-4836-8B42-80FB-12A69365F0B0";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3146772384643484 0.30593535304068098 -2.3912868499755913 ;
	setAttr ".r" -type "double3" -27.769049129171496 -19.527703069996946 11.850627289629651 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999978 0.99999999999999944 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.50165929985300162 0.81946977563333701 -0.27714118007695171 0
		 -0.86150484141930728 0.50229885136728791 -0.074197521024615631 0 0.078405070512635011 0.27598034484099043 0.95796006919879284 0
		 -50.945100964285352 101.90399945334072 16.074200470938983 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_01_r" -p "pinky_metacarpal_r";
	rename -uid "1DC3915A-4E36-1910-A5C7-78AB52563EFD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.9573006629943919 0.14326146245002747 0.19892024993895774 ;
	setAttr ".r" -type "double3" 10.491640062438105 0.60504264270136832 14.833680882858816 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.2635405017551955 0.91778928814850058 -0.29700038130361062 0
		 -0.93037057822879088 0.32317414573263875 0.1731157378640259 0 0.25486661433158819 0.23069740806920463 0.93905362722759578 0
		 -53.539801031310596 97.968499538497568 17.628000637701916 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_02_r" -p "pinky_01_r";
	rename -uid "4CE20B37-4137-CB38-DEB2-D1BB1BC00932";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.8160362243652344 3.0366025399075625e-05 3.2629206547341028e-05 ;
	setAttr ".r" -type "double3" 6.3611093629270367e-15 1.4312496066585827e-14 21.28699904924385 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.092201469831037886 0.97249693640582791 -0.21388921815341003 0
		 -0.96257046384155742 -0.032068903807761784 0.26912764173978709 0 0.25486661433158825 0.23069740806920469 0.939053627227596 0
		 -54.545501068157023 94.466199709576202 18.761400748818435 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "pinky_03_r" -p "pinky_02_r";
	rename -uid "33D9948E-4982-2308-E9CA-B681CF62E12E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.0399997234344625 -1.7523876529423887e-05 -3.1002964529847077e-05 ;
	setAttr ".r" -type "double3" 1.7075473052254064e-06 9.5416640325420615e-15 4.9170000470223654 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000007 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.17436652109961143 0.96616935149040684 -0.19003447203133475 0
		 -0.95112528657901119 -0.1153060647374114 0.28647024394301029 0 0.25486664267733117 0.2306974115055935 0.93905361869011839 0
		 -54.357401128856097 92.482299637935398 19.197700865091143 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_metacarpal_r" -p "hand_r";
	rename -uid "5F13B0EA-465C-7FF7-9AEC-83B6CB80EC5F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.3742079734802175 0.54299175739286909 -1.0917816162109411 ;
	setAttr ".r" -type "double3" -13.299834889366398 -11.809318654920911 -1.5945633604277225 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999978 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.59060503119176344 0.65963271076872343 -0.46483371652116912 0
		 -0.73083333885388824 0.68147046384253407 0.038479055730619577 0 0.3421524922467386 0.31699005314701523 0.8845614609823319 0
		 -50.33090093933658 102.40499942786849 17.132600610165039 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_01_r" -p "ring_metacarpal_r";
	rename -uid "2790B1A2-455B-B93E-5AD8-63A09ACAC955";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.6457118988037216 0.041443493217229843 0.02067497372626903 ;
	setAttr ".r" -type "double3" 6.3958444445851219 -0.1169380136585665 29.414482479749058 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.15623819409077647 0.90993079452602965 -0.38420772490995236 0
		 -0.88283473504289867 0.30308700144821343 0.35880510051400683 0 0.44293617746689906 0.28313286408744437 0.85067227765141862 0
		 -53.688501084163399 98.715699461407652 19.776800845944017 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_02_r" -p "ring_01_r";
	rename -uid "EC6BC5C8-4A26-B18A-8841-66BEC5BE7EAD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.9770674705505371 -2.0846833649557084e-05 -2.3612021323060617e-05 ;
	setAttr ".r" -type "double3" 9.5416640443905487e-15 -3.1805546814635152e-15 18.963999541971834 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.13914028536523607 0.95903783110518104 -0.24675173656441018 0
		 -0.88569042203215298 -0.0090675124875544411 0.46418773846127842 0 0.44293617746689917 0.28313286408744442 0.85067227765141884 0
		 -54.466101171939769 94.186899499776416 21.68900104948537 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ring_03_r" -p "ring_02_r";
	rename -uid "B831BC2D-43F3-028F-ACF2-86B8FD72BCD6";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.2649745941161967 5.0017570174532011e-05 -1.1221488421142567e-05 ;
	setAttr ".r" -type "double3" 6.3611093629270367e-15 -6.3611093629270335e-15 9.1679997480249735 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.27847973581370661 0.9453417871894092 -0.16964062642734823 0
		 -0.85220688769344044 -0.16175502053159105 0.49757284280865344 0 0.44293617746689917 0.28313286408744442 0.85067227765141884 0
		 -54.151001231055453 92.014699546819784 22.24790113559148 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_01_r" -p "hand_r";
	rename -uid "35E1D956-4472-89CC-CC8C-44BA36F6CD22";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -1.9928325414657593 -1.3566571474075317 2.5813255310058487 ;
	setAttr ".r" -type "double3" 73.564463907750024 39.90417842702314 20.508675504416569 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 0.99999999999999867 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.23677732944738347 0.46744570505413874 -0.85172237794143069 0
		 0.35804510679136936 0.85693276787520078 0.37076937959398015 0 0.90318336884739048 -0.21716524622551259 -0.37026889967872045 0
		 -46.226701019175849 102.95799948474078 18.495800563608931 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_02_r" -p "thumb_01_r";
	rename -uid "31B1894A-492E-F493-0A98-1DB8B1E37F25";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.3778247833251811 0.00042712956201285124 -0.00013574546028394252 ;
	setAttr ".r" -type "double3" 3.5306280002014754 -1.9322904957701323 23.246005781061324 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.0457449849891126 0.75995290887936373 -0.64836638764986898 0
		 0.47737462528905472 0.5867702494000363 0.6540750274617998 0 0.8775083267288577 -0.27959300904138068 -0.38962403136447582 0
		 -45.190101029584021 100.91199959280999 22.224700527158511 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thumb_03_r" -p "thumb_02_r";
	rename -uid "2F998A23-4F6E-8F62-0D10-149D2789645E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.0859522819519114 -1.4851160820228415e-05 4.5825581779013191e-05 ;
	setAttr ".r" -type "double3" 1.2722218725854065e-14 1.5902773407317588e-15 9.9999999709533913 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.037845217624813174 0.85029910088001526 -0.52493730915754966 0
		 0.47806576537590534 0.44589145353754533 0.75672579950582219 0 0.87750832672885792 -0.27959300904138074 -0.38962403136447593 0
		 -45.048901066006756 98.566799652746084 24.225500692146209 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_metacarpal_r" -p "hand_r";
	rename -uid "6A11343B-48B5-D249-3E15-E484B12A5A19";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -3.4445140361785747 0.38516682386398315 2.3793087005615163 ;
	setAttr ".r" -type "double3" 3.2877464546581714 7.3255016683865106 -0.60616237917610172 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.38282471693548581 0.58595958989830976 -0.71421046975626912 0
		 -0.60140250134155437 0.74492304281562782 0.28879870439880584 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -48.139100880562282 103.230999608392 19.700100530986685 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_01_r" -p "index_metacarpal_r";
	rename -uid "9DBB064B-455F-F4CA-79A2-1C8311AEB15F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -5.8772053718566966 -0.043412361294045354 -0.24095164239406408 ;
	setAttr ".r" -type "double3" 9.541664044390555e-15 -3.5311250384401278e-31 23.372999646513961 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.11282515359989806 0.83339914156584305 -0.54103267512459574 0
		 -0.70392486618372341 0.45133673853211353 0.54843863031283946 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.531900895495319 99.677999863184866 23.731500561889256 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_02_r" -p "index_01_r";
	rename -uid "FA8A9994-457D-035B-D215-72A4E38D898E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -4.079932689666748 5.0402059201815064e-06 3.2106661814523818e-05 ;
	setAttr ".r" -type "double3" 9.5416640443905582e-15 -1.5902773407317598e-15 14.892568419110976 ;
	setAttr ".s" -type "double3" 0.99999999999999956 0.99999999999999956 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.071878640927211662 0.9214016860637716 -0.38190626323391952 0
		 -0.70927652822793308 0.2219862915369494 0.66906568651710374 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.992200960814621 96.277799977819839 25.938900693876729 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "index_03_r" -p "index_02_r";
	rename -uid "5734A99F-4783-A1A6-5173-B2B8A8E05C82";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.5950763225555562 3.9602185992748673e-05 -3.5606819821509816e-06 ;
	setAttr ".r" -type "double3" 3.1805546814635168e-15 -4.4139062980501597e-32 12.516400997546972 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.22388412433854538 0.94761232662282568 -0.22783058903851844 0
		 -0.67684239774542487 0.017025250188002911 0.73593104939950804 0 0.70125620673430589 0.31896868073293855 0.63757251605452758 0
		 -50.80570098749827 93.886699934149348 26.930000821301533 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "weapon_r" -p "hand_r";
	rename -uid "181F31E4-48AD-061E-760B-1CA9D595B3BE";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -1.1633833646774221 -1.3170545101165771 -0.51951736211777799 ;
	setAttr ".r" -type "double3" -11.617611866448334 -15.808370499724777 8.5170885216315799 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999967 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.51015706085696022 0.78377149596726137 -0.35417794308374112 0
		 -0.79058850044401541 0.58949099082372403 0.16574134880393657 0 0.33868805149203512 0.1954548895446358 0.92037372296780728 0
		 -47.768320898672442 102.63395111216924 15.698805434373773 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_01_r" -p "upperarm_r";
	rename -uid "35AC778A-4592-3081-1FF0-9B88CE576CFA";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -9.2568979263305522 1.0202637897194222e-05 -0.00010078256310919187 ;
	setAttr ".r" -type "double3" 2.6828754950018744e-10 -2.153331239563208 -0.32660888591551801 ;
	setAttr ".s" -type "double3" 1.0000000000000002 0.99999999999999978 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.60649254765026761 0.79463176670612623 -0.026965626011451752 0
		 -0.029307966948783556 0.056235375135533512 0.99798728732218578 0 0.79454882336960109 -0.60448154473471449 0.057395377489094922 0
		 -24.342249087200909 136.01932912929374 -2.3405260850142464 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "upperarm_twist_02_r" -p "upperarm_r";
	rename -uid "0DAAC6CE-4D61-2C2F-1970-0C9ECA01D5F9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -18.513795852661133 2.0405275791723909e-05 -0.00020156512620417288 ;
	setAttr ".r" -type "double3" 1.987846675914698e-15 1.0597707590970231e-14 -1.1927080055488186e-15 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.57603356970190356 0.81709064454343172 -0.023413781755254943 0
		 -0.032592100702963554 0.051578494510997164 0.99813697150027847 0 0.81677602899953594 -0.57419729841194711 0.056341644883428695 0
		 -29.674615693378339 128.45566283150771 -2.1237825918617612 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_r" -p "pelvis";
	rename -uid "E0019149-46BA-68FD-CDD0-E9BB5D16482E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.3657262325286723 -0.11948779225349782 9.9690914154052734 ;
	setAttr ".r" -type "double3" 8.4085386612241084 -3.1255399000842652 176.43986665923373 ;
	setAttr ".s" -type "double3" 1 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.054523910657437981 -0.99851165534365671 0.0012717348352381946 0
		 -0.14601293308005975 0.0092329884397982023 0.98923959448549603 0 -0.98777900693423204 0.053751521535134156 -0.14629903414814571 0
		 -9.9690914154052734 93.543381742615168 2.550023234662302 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_r" -p "thigh_r";
	rename -uid "6EFB2620-405B-B189-E3C7-EC9FDA3A59F3";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 43.341262817382777 -2.5757174171303632e-14 1.0658141036401503e-14 ;
	setAttr ".r" -type "double3" -6.3611093629270351e-15 -4.6714396883995417e-15 -5.0048445558743904 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999989 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.041577864212587176 -0.9955101408023912 -0.085034350512737847 0
		 -0.15021289780688588 -0.07791234492852539 0.98557889173835111 0 -0.98777900693423204 0.053751521535134156 -0.14629903414814571 0
		 -12.332226557040798 50.266625662145813 2.6051418283903547 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "foot_r" -p "calf_r";
	rename -uid "9CFC202D-4E26-D2DD-9DAA-9C98EA3287C1";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 42.217948913574233 1.1102230246251565e-16 1.0658141036401503e-14 ;
	setAttr ".r" -type "double3" -0.0046626083855055749 3.0812019613373725 2.6641047060062926 ;
	setAttr ".s" -type "double3" 0.99999999999999989 1.0000000000000002 1.0000000000000002 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495256007424712 -0.99950197930304507 -0.031211781124816901 0
		 -0.14803750047914047 -0.031556184277057628 0.98847817663606585 0 -0.98897081876240256 2.4559475175288392e-05 -0.14811049602663431 0
		 -14.087558704303341 8.2382293948053729 -0.98483403745537856 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ball_r" -p "foot_r";
	rename -uid "49FB8D1B-4B1E-46BF-5CD4-099BDB5CF115";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 7.0094366073608354 15.237594604492184 -0.53894561529159546 ;
	setAttr ".r" -type "double3" 6.9773418324605905e-14 -6.5201370970002121e-14 -90.000000000000014 ;
	setAttr ".s" -type "double3" 0.99999999999999967 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.14803750047914041 0.031556184277057836 -0.98847817663606552 0
		 0.0046495256007425042 -0.99950197930304507 -0.031211781124817119 0 -0.98897081876240234 2.4559475175288385e-05 -0.14811049602663429 0
		 -15.777702081490759 0.75143005244908334 13.938242194727604 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_02_r" -p "calf_r";
	rename -uid "2560E8B0-4226-8503-83B0-948AD31A328B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.072649955749519 6.8833827526759706e-15 0.037728950381282544 ;
	setAttr ".r" -type "double3" -0.0046559128746518717 0.25816272471228668 2.6643342814062057 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999967 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.044064310719183021 -0.99828778764580239 -0.038468552846355794 0
		 -0.14803750057573373 -0.031556185440510864 0.98847817658445691 0 -0.98799961282590232 0.049251397926289076 -0.14639352737800071 0
		 -12.954605151152517 36.259187911723764 1.4029634704098872 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_01_r" -p "calf_r";
	rename -uid "A00D6B1E-4267-F376-0444-33B46EA0E48F";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 28.145299911499034 8.4376949871511897e-15 0.075457900762563312 ;
	setAttr ".r" -type "double3" -0.0046559128746518717 0.25816272471228668 2.6643342814062057 ;
	setAttr ".s" -type "double3" 0.99999999999999989 0.99999999999999967 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.044064310719183021 -0.99828778764580239 -0.038468552846355794 0
		 -0.14803750057573373 -0.031556185440510864 0.98847817658445691 0 -0.98799961282590232 0.049251397926289076 -0.14639352737800071 0
		 -13.576983745264235 22.251750161301715 0.20078511242941532 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_01_r" -p "thigh_r";
	rename -uid "94E79264-4DB5-6F82-F9D1-21A0F699C9B8";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.447087287902804 -3.5527136788005009e-15 -3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" -2.065027893746282e-10 0.25820470285918773 -1.3073006136480809 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 -0.99869449405102062 -0.02063830699820695 0
		 -0.14721887520437615 -0.013550178981221524 0.98901111997445978 0 -0.98799961282742133 0.049251397967495933 -0.14639352735388469 0
		 -10.75680311195109 79.117796699877033 2.568396098834052 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_02_r" -p "thigh_r";
	rename -uid "18E5C04C-403F-E0F5-7FD8-01BE66A9C1E4";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 28.894174575805629 -1.2434497875801753e-14 -3.3750779948604759e-14 ;
	setAttr ".r" -type "double3" -2.065027893746282e-10 0.25820470285918773 -1.3073006136480809 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 -0.99869449405102062 -0.02063830699820695 0
		 -0.14721887520437615 -0.013550178981221524 0.98901111997445978 0 -0.98799961282742133 0.049251397967495933 -0.14639352735388469 0
		 -11.544514808496881 64.692211657138884 2.5867689630058006 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_l" -p "pelvis";
	rename -uid "ABF127DA-4C3B-83BA-0248-DE862D31578E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -2.3657112121582031 -0.11004376411438344 -9.969202995300293 ;
	setAttr ".r" -type "double3" 8.4085386612241031 -3.1255399000842647 -3.5601333407662921 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.05452391065743796 0.99851165534365638 -0.0012717348352376742 0
		 -0.14601293308005966 -0.0092329884397976889 -0.98923959448549603 0 -0.98777900693423215 -0.053751521535134204 0.1462990341481456 0
		 9.969202995300293 93.542798291234817 2.5405972345779255 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_l" -p "thigh_l";
	rename -uid "8159BDC0-4E3E-3A08-9E7A-7B8FEAD47FD8";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -43.341308593749993 6.2172489379008766e-15 5.3290705182007514e-15 ;
	setAttr ".r" -type "double3" -3.1805546814635187e-15 0 -5.0048445558743548 ;
	setAttr ".s" -type "double3" 0.99999999999999967 0.99999999999999967 0.99999999999999989 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.041577864212587252 0.99551014080239086 0.085034350512737736 0
		 -0.15021289780688574 0.077912344928525237 -0.98557889173835078 0 -0.98777900693423204 -0.053751521535134197 0.14629903414814557 0
		 12.33234063284236 50.265996502529269 2.5957158865213779 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "foot_l" -p "calf_l";
	rename -uid "06569D4E-4180-FE4F-3428-D38026C790C2";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -42.217914581298842 -3.5527136788005009e-15 5.3290705182007514e-15 ;
	setAttr ".r" -type "double3" -0.0046626083855039946 3.0812019613373756 2.6641047060062952 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000011 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495256007424504 0.9995019793030453 0.031211781124816786 0
		 -0.14803750047914047 0.031556184277057475 -0.9884781766360663 0 -0.98897081876240278 -2.455947517530227e-05 0.14811049602663423 0
		 14.087671352642205 8.2376344133171457 -0.99425705990160473 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ball_l" -p "foot_l";
	rename -uid "D1AE89E4-41EC-08A6-ED81-9EAE7C45951C";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -7.0094366073608327 -15.237588882446284 0.53888744115829468 ;
	setAttr ".r" -type "double3" 9.0447023754118737e-15 -6.3611093629270367e-15 -90.000000000000014 ;
	setAttr ".s" -type "double3" 0.99999999999999956 1.0000000000000002 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.14803750047914041 -0.031556184277057683 0.98847817663606585 0
		 0.0046495256007424842 0.99950197930304552 0.031211781124817012 0 -0.98897081876240256 -2.4559475175302263e-05 0.1481104960266342 0
		 15.777871415272493 0.75083525295552001 13.928804899964147 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_02_l" -p "calf_l";
	rename -uid "DC7AFFE9-40C4-D42B-6D8F-FBBA73804215";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.072638511657715 1.7763568394002505e-15 1.9539925233402755e-14 ;
	setAttr ".r" -type "double3" -0.0046559128746502809 0.2581627247122899 2.6643342814062074 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.04406431071918307 0.99828778764580262 0.03846855284635569 0
		 -0.14803750057573373 0.031556185440510726 -0.98847817658445736 0 -0.98799961282590276 -0.049251397926289082 0.14639352737800065 0
		 12.917450885992871 36.256542156327747 1.3990582106820248 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "calf_twist_01_l" -p "calf_l";
	rename -uid "9F783A2C-4EEB-FA92-025E-D5973763413A";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -28.145277023315437 5.0670109880135428e-06 -0.075448110699655402 ;
	setAttr ".r" -type "double3" -0.0046559128746502809 0.2581627247122899 2.6643342814062074 ;
	setAttr ".s" -type "double3" 1.0000000000000004 1.0000000000000004 1.0000000000000004 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.04406431071918307 0.99828778764580262 0.03846855284635569 0
		 -0.14803750057573373 0.031556185440510726 -0.98847817658445736 0 -0.98799961282590276 -0.049251397926289082 0.14639352737800065 0
		 13.577086437874987 22.251143655655984 0.19135755517993358 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_01_l" -p "thigh_l";
	rename -uid "63C0BBD9-4C2A-2F97-16E8-6E8EF51A44EF";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.447102546691895 8.8817841970012523e-16 3.5527136788005009e-15 ;
	setAttr ".r" -type "double3" -2.0649642897718216e-10 0.25820470285919295 -1.3073006136480436 ;
	setAttr ".s" -type "double3" 0.99999999999999978 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 0.99869449405102062 0.020638306998206814 0
		 -0.14721887520437604 0.013550178981221378 -0.98901111997445978 0 -0.98799961282742133 -0.049251397967495884 0.14639352735388458 0
		 10.756915523814962 79.117198012417944 2.5589701181548041 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "thigh_twist_02_l" -p "thigh_l";
	rename -uid "818E24E9-4EE3-F0AD-9DAD-0187121D5C05";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -28.894205093383796 -2.2688980125806779e-06 -8.0748641266836785e-06 ;
	setAttr ".r" -type "double3" -2.0649642897718216e-10 0.25820470285919295 -1.3073006136480436 ;
	setAttr ".s" -type "double3" 0.99999999999999978 1 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" -0.046726521766803475 0.99869449405102062 0.020638306998206814 0
		 -0.14721887520437604 0.013550178981221378 -0.98901111997445978 0 -0.98799961282742133 -0.049251397967495884 0.14639352735388458 0
		 11.544636359799362 64.691598188585999 2.5773440648706107 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_root" -p "root";
	rename -uid "9F4B705B-4C3C-09FB-B299-D9BADBBD8BD9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_gun" -p "ik_hand_root";
	rename -uid "10CCB98E-4E10-AF73-95FF-448C8D2898C0";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -47.768318176269531 -15.69880485534668 104.4664306640625 ;
	setAttr ".r" -type "double3" 68.473107478131155 -39.410111911239163 53.666512015145315 ;
	setAttr ".s" -type "double3" 0.99999999999999978 0.99999999999999978 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776599577967658 0.63486688008580827 -0.62241010409371778 0
		 -0.64550907761389853 0.71872766733298943 0.25835744798269883 0 0.61136594918746878 0.28350411774821049 0.7388214205028939 0
		 -47.768318176269531 104.4664306640625 15.69880485534668 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_r" -p "ik_hand_gun";
	rename -uid "CAD41385-40AE-C1C5-9031-079E586BAE91";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -7.1054273576010019e-15 0 7.1054273576010019e-15 ;
	setAttr ".r" -type "double3" 3.3395824155366921e-14 -2.2263882770244611e-14 0 ;
	setAttr ".s" -type "double3" 1.0000000000000002 1.0000000000000002 1 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.45776599577967669 0.63486688008580838 -0.62241010409371789 0
		 -0.64550907761389864 0.71872766733298954 0.25835744798269888 0 0.61136594918746878 0.28350411774821049 0.7388214205028939 0
		 -47.768318176269531 104.4664306640625 15.698804855346689 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_hand_l" -p "ik_hand_gun";
	rename -uid "E288A28D-4213-90CF-57FF-1A86D88D9313";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 43.73357009887696 -61.669849395751982 58.408111572265597 ;
	setAttr ".r" -type "double3" -107.73758596138391 -34.036790747396616 -134.50699481505316 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.4577661185092996 -0.63486684526340853 0.62241004934867228 0
		 -0.64550905383748758 -0.71872771643705491 -0.25835737078513543 0 0.61136588239675338 -0.28350407124142618 -0.73882149361721683 0
		 47.768601260708806 104.46653900739912 15.698887991063685 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_root" -p "root";
	rename -uid "FF577E90-435D-7DEF-2437-51989EEFF501";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_l" -p "ik_foot_root";
	rename -uid "5946C9F4-4810-2EDD-A782-E4BAF498FBD5";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 14.087671279907227 0.99425750970840454 8.2376375198364258 ;
	setAttr ".r" -type "double3" 90.044595639783211 -88.191663071784689 -81.527131053351226 ;
	setAttr ".s" -type "double3" 1 0.99999999999999978 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495233472996222 0.99950197930433926 0.031211781419062105 0
		 -0.14803749178976766 0.031556184234514777 -0.98847817793877035 0 -0.98897082007369519 -2.4561468946027169e-05 0.14811048727047271 0
		 14.087671279907227 8.2376375198364258 -0.99425750970840454 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "ik_foot_r" -p "ik_foot_root";
	rename -uid "B00FB116-4FAE-8029-E326-E49ED1DD9E6E";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" -14.087558746337891 0.98483455181121826 8.2382316589355469 ;
	setAttr ".r" -type "double3" -89.955404360215979 88.191663071784689 81.527131053350843 ;
	setAttr ".s" -type "double3" 1 0.99999999999999956 0.99999999999999978 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 0.0046495233473000663 -0.99950197930433893 -0.031211781419062216 0
		 -0.14803749178978831 -0.031556184234514895 0.9884781779387668 0 -0.98897082007369175 2.4561468946471259e-05 -0.14811048727049336 0
		 -14.087558746337891 8.2382316589355469 -0.98483455181121826 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "interaction" -p "root";
	rename -uid "254C8694-4B9E-21E2-BEC2-9EAC0E42C1BD";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "center_of_mass" -p "root";
	rename -uid "4A582CD3-491A-0B5E-22C6-63A1503A1DC9";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 0 0 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "camera_root" -p "root";
	rename -uid "1F22F15A-467C-970B-3316-848DC2196B50";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 2.8421709430404007e-14 0 168 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 2.8421709430404007e-14 168 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode joint -n "camera_bone" -p "camera_root";
	rename -uid "B9EA8EA4-4C46-4862-F8D4-6888B94FE14B";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".t" -type "double3" 0 0 -3 ;
	setAttr ".ssc" no;
	setAttr ".bps" -type "matrix" 1 0 0 0 0 0 -1 0 0 1 0 0 2.8421709430404007e-14 165 0 1;
	setAttr ".radi" 3;
	setAttr ".fbxID" 5;
createNode transform -n "MainHero_Cape";
	rename -uid "611B88D2-43F8-DEB6-F442-749E8BBCEA10";
createNode transform -n "Cape" -p "MainHero_Cape";
	rename -uid "5898B812-49EB-3E85-735A-83A3198F231A";
	setAttr -l on ".tx";
	setAttr -l on ".ty";
	setAttr -l on ".tz";
	setAttr -l on ".rx";
	setAttr -l on ".ry";
	setAttr -l on ".rz";
	setAttr -l on ".sx";
	setAttr -l on ".sy";
	setAttr -l on ".sz";
	setAttr ".it" no;
createNode mesh -n "CapeShape" -p "Cape";
	rename -uid "05CD477E-4636-04E9-8DC9-0092198C14E7";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr ".ndt" 0;
	setAttr ".vcs" 2;
createNode mesh -n "CapeShapeOrig" -p "Cape";
	rename -uid "FBDE5CF3-41AD-89BE-386C-EEA9219416AF";
	setAttr -k off ".v";
	setAttr ".io" yes;
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr -s 1174 ".uvst[0].uvsp";
	setAttr ".uvst[0].uvsp[0:249]" -type "float2" 0.072004013 0.036654592 0.082303159
		 0.041666567 0.074147403 0.045339108 0.064504564 0.041900277 0.061266907 0.033695698
		 0.055933919 0.035482109 0.056455035 0.045195937 0.04757902 0.045753717 0.057038628
		 0.052510977 0.065983593 0.049454987 0.066599101 0.057561159 0.074999444 0.05438143
		 0.075190991 0.063462138 0.082920715 0.061415434 0.08278393 0.070751071 0.075114071
		 0.072495401 0.066701353 0.065956354 0.06665352 0.074555516 0.057505887 0.068304956
		 0.057469871 0.076634169 0.047697283 0.070247054 0.04765809 0.062051296 0.037352011
		 0.063299716 0.037242386 0.071826398 0.047652863 0.078480601 0.037142184 0.080179334
		 0.047599357 0.086760283 0.037058797 0.088488936 0.04744985 0.095051289 0.036973707
		 0.096830189 0.047171291 0.10340393 0.036770351 0.105196 0.046806503 0.11167878 0.036522124
		 0.1133855 0.046328224 0.11979729 0.036164835 0.12133849 0.045853805 0.12781066 0.035856731
		 0.12907207 0.045413129 0.13572013 0.035511713 0.13682562 0.045031302 0.14365935 0.035281435
		 0.14456725 0.044800114 0.15144736 0.035213839 0.15221143 0.044498377 0.15919787 0.035107393
		 0.15978467 0.044147447 0.1668551 0.03487166 0.16700518 0.043816514 0.17450416 0.034618661
		 0.17438817 0.043474674 0.18217826 0.053242717 0.17484343 0.05300517 0.18259656 0.043298017
		 0.18962306 0.052902013 0.19018596 0.043311425 0.19693333 0.033816148 0.19670987 0.033952024
		 0.20393473 0.043363117 0.20423543 0.034146968 0.21132469 0.043426849 0.21157193 0.034340557
		 0.21880269 0.043447636 0.21905327 0.03445223 0.22642267 0.043417647 0.22665519 0.034524936
		 0.23422325 0.043384701 0.23440361 0.034696255 0.24220586 0.043421395 0.24227279 0.035045817
		 0.25038093 0.043531477 0.25035179 0.035469342 0.25859851 0.043858211 0.25858384 0.035898201
		 0.26683068 0.044239014 0.26687479 0.036410224 0.27507424 0.044528481 0.27524853 0.037171949
		 0.28312278 0.045152064 0.28338885 0.038212463 0.29092491 0.046334356 0.29124409 0.039425202
		 0.2984817 0.047750905 0.29881644 0.054556906 0.29205787 0.053441413 0.28414136 0.061543763
		 0.28521484 0.062713452 0.29317015 0.056108985 0.29967487 0.064396515 0.30083823 0.070750706
		 0.29441404 0.069413461 0.28648376 0.07717704 0.28781962 0.076499954 0.27966022 0.084271826
		 0.28104401 0.084288411 0.27268159 0.092509605 0.27414715 0.093588628 0.26626265 0.10233853
		 0.26789498 0.10364386 0.26025188 0.11248965 0.26174939 0.11371795 0.25417072 0.12140372
		 0.26279116 0.12040876 0.27027941 0.12961674 0.27065521 0.11956115 0.27748668 0.11031456
		 0.2766242 0.11012757 0.28368682 0.10117396 0.28294826 0.10218789 0.29057044 0.093701087
		 0.28993368 0.095203303 0.29752296 0.086884983 0.29667902 0.08846695 0.30431581 0.080504663
		 0.30331922 0.08243607 0.31109917 0.074519686 0.30979431 0.076330453 0.31760424 0.068155155
		 0.31602788 0.069571711 0.32388067 0.061212603 0.32202774 0.062236879 0.32982445 0.053489242
		 0.32769072 0.054016031 0.33519626 0.044652425 0.33347404 0.044013847 0.32629561 0.03490949
		 0.33302474 0.035481267 0.34015679 0.045015171 0.34076369 0.035667695 0.34695369 0.04481386
		 0.34774995 0.054304019 0.34281337 0.05458951 0.35098684 0.063550614 0.34621888 0.063042559
		 0.33790809 0.071667962 0.34086657 0.070616655 0.33209658 0.07847669 0.33414519 0.077657707
		 0.3256532 0.085392207 0.32722223 0.084205367 0.31904685 0.091602571 0.32020962 0.090066284
		 0.31215411 0.097687401 0.3130517 0.096571006 0.30518949 0.10453453 0.30593455 0.1034388
		 0.29818606 0.11166635 0.2987321 0.11081669 0.29108924 0.11955103 0.29148269 0.11927373
		 0.284289 0.12850578 0.28472018 0.1289451 0.27776611 0.13757867 0.28492403 0.13701144
		 0.29215956 0.14568193 0.29241514 0.14474662 0.29995 0.15293109 0.30031401 0.15156546
		 0.30801976 0.14381175 0.30771661 0.150295 0.31584382 0.14290041 0.3157059 0.14921677
		 0.32383442 0.15631178 0.32375908 0.15518209 0.33168191 0.14835028 0.33196723 0.15427417
		 0.33976185 0.16090451 0.33938277 0.16001759 0.34740126 0.16656174 0.34704185 0.16575775
		 0.35490692 0.15926065 0.35554886 0.15349209 0.34791911 0.15274626 0.35621744 0.14688183
		 0.34841603 0.14618419 0.35680264 0.15198158 0.36475116 0.15855606 0.36390072 0.1577681
		 0.37206256 0.16426292 0.37055868 0.16364513 0.37787193 0.16994537 0.37591183 0.16367082
		 0.3851186 0.15702558 0.3800782 0.15660965 0.38820106 0.15037771 0.3823365 0.1511851
		 0.37339139 0.14458404 0.37413484 0.14362998 0.38307369 0.13815953 0.37463337 0.13892841
		 0.36584842 0.13247913 0.36610055 0.13183738 0.37500608 0.13738702 0.38359052 0.13118982
		 0.38370204 0.13680388 0.39204109 0.14343628 0.39220524 0.1419351 0.40101469 0.14582905
		 0.40259588 0.15070558 0.39288306 0.15479174 0.40828449 0.16041534 0.40125465 0.15962088
		 0.41201544 0.16400379 0.40878856 0.16977517 0.40606171 0.16812451 0.41477096 0.16351631
		 0.41619557 0.16583365 0.42060709 0.17113221 0.42061484 0.17374298 0.41327578 0.17687315
		 0.42022645 0.18255685 0.41961861 0.17954288 0.41195786 0.18778917 0.41879451 0.18511479
		 0.41081667 0.18219729 0.40282845 0.18784361 0.40177387 0.18465661 0.39011669 0.17878626
		 0.39130545 0.18272442 0.37941122 0.17640965 0.38064444 0.18301968 0.37347221 0.17640406
		 0.37434483 0.17733303 0.3680321 0.17063574 0.3690784 0.17155108 0.36203599 0.16500387
		 0.36288965 0.17241265 0.35449147 0.17833413 0.36143196 0.17938247 0.35442007 0.18522555
		 0.36145878 0.18404336 0.36769056 0.19089629 0.36772907 0.18976456 0.37327945 0.19200803
		 0.36186969 0.18645374 0.35473192 0.19352593 0.3556208 0.18791142 0.34799242 0.1806168
		 0.34736025 0.17339012 0.34700358 0.17470488 0.33977509 0.16767405 0.33933008 0.16911593
		 0.33188152 0.16206831 0.33154672 0.16353506 0.32392704 0.15768732 0.31599081 0.16520981
		 0.31636739 0.17084898 0.32450455 0.17277688 0.3170718 0.16703287 0.30879742 0.17475203
		 0.30947948;
	setAttr ".uvst[0].uvsp[250:499]" 0.18034199 0.3180716 0.17827085 0.32541418
		 0.18569712 0.3265785 0.18778703 0.31932986 0.19317919 0.32799709 0.19125324 0.33482516
		 0.19873521 0.33629966 0.20067014 0.32966852 0.19517435 0.32086289 0.20254566 0.32261652
		 0.19711995 0.313317 0.18975717 0.31172037 0.19171935 0.30373931 0.18420731 0.3025322
		 0.18232043 0.31044519 0.17664266 0.30168533 0.16890974 0.30114055 0.17057486 0.29331219
		 0.16268028 0.29302084 0.16096973 0.30070174 0.15427391 0.2926904 0.15545747 0.28513753
		 0.14659475 0.2850526 0.14746167 0.27770209 0.13822623 0.27781081 0.13894795 0.27055651
		 0.13046445 0.26319623 0.13965391 0.26302683 0.13131432 0.255647 0.12245866 0.25526404
		 0.12345078 0.24747205 0.11485516 0.24643052 0.10497316 0.25257587 0.10619238 0.24481791
		 0.11581331 0.2384885 0.10723289 0.23695481 0.11657888 0.23030829 0.12484687 0.23105687
		 0.12528358 0.22242725 0.13305841 0.23117489 0.13262057 0.23959976 0.12423488 0.23939562
		 0.13203868 0.24781597 0.14070669 0.24740505 0.14026758 0.25536448 0.14927176 0.25460684
		 0.14885846 0.26250404 0.15774162 0.26174968 0.15715122 0.26974487 0.16552962 0.26919824
		 0.1647879 0.27730906 0.15640527 0.27753109 0.14825293 0.27022016 0.16391779 0.28525579
		 0.17186463 0.28527367 0.17824687 0.29367083 0.17961663 0.28542978 0.18590219 0.29435945
		 0.18743564 0.28597713 0.18073507 0.27705145 0.17279448 0.27706647 0.17361233 0.268682
		 0.16624126 0.2609182 0.17448835 0.26017898 0.16685644 0.25252467 0.15818435 0.2535789
		 0.15841872 0.24528074 0.14952271 0.24647164 0.14970334 0.23815799 0.14105864 0.23915434
		 0.1413748 0.23064762 0.13341343 0.22238088 0.14163609 0.22176778 0.1336295 0.21327573
		 0.12554486 0.21347696 0.11708035 0.22190911 0.11737391 0.21314704 0.12565188 0.20423806
		 0.11752727 0.20415479 0.12561747 0.19472849 0.13369994 0.20387512 0.14179628 0.21256083
		 0.14184785 0.20310181 0.15018435 0.21142989 0.15006858 0.22065443 0.1498867 0.22959507
		 0.15864058 0.22821605 0.1585281 0.23687798 0.16746081 0.23555076 0.1673037 0.24405968
		 0.17604826 0.24303365 0.17534664 0.25162232 0.18375732 0.25105882 0.18271191 0.25976354
		 0.18170355 0.2684716 0.18989235 0.26873446 0.18877289 0.27744126 0.1970669 0.27832854
		 0.19542712 0.28699386 0.20354004 0.28853893 0.20136142 0.29710352 0.20899913 0.29917932
		 0.21157388 0.29058629 0.20556223 0.27972901 0.21411501 0.28158969 0.20719008 0.27065873
		 0.19838449 0.26946616 0.19951567 0.26046133 0.19102409 0.25985008 0.19221605 0.25091988
		 0.18466468 0.24234939 0.19318862 0.24206239 0.18516739 0.23368382 0.17639226 0.23442721
		 0.17651938 0.22556865 0.16755977 0.22678506 0.16765611 0.21774012 0.15875305 0.21922755
		 0.15884939 0.21000129 0.15022899 0.2019639 0.15888722 0.20056701 0.16774368 0.20847702
		 0.16783707 0.19907701 0.15891142 0.19097686 0.1502099 0.19232017 0.15021537 0.18251258
		 0.14179628 0.18356687 0.14178583 0.17359924 0.13350216 0.17445046 0.13359803 0.18440479
		 0.12529369 0.17517424 0.12503137 0.16535485 0.11664455 0.16618258 0.11705148 0.17580211
		 0.12550262 0.18501103 0.11736719 0.18541491 0.13366552 0.19424725 0.14182672 0.19343734
		 0.11752658 0.19487751 0.10916965 0.1947183 0.10915771 0.20364493 0.10038815 0.20282561
		 0.10020002 0.21120536 0.10897651 0.21235794 0.0998208 0.21935034 0.10862003 0.22081834
		 0.099243008 0.22725314 0.090180002 0.22548598 0.089447245 0.23320049 0.098434471
		 0.2350952 0.088541582 0.24093634 0.09742213 0.24288857 0.087467663 0.24871671 0.078679137
		 0.2468667 0.077803008 0.25474453 0.069500141 0.2531029 0.069346771 0.26130515 0.077189431
		 0.26283562 0.069128424 0.26972818 0.07669206 0.27117455 0.068943128 0.27822733 0.061133083
		 0.27694696 0.06111116 0.26851672 0.052954499 0.27593017 0.052772049 0.26755142 0.061093774
		 0.2600956 0.052549042 0.25916392 0.060974039 0.25180614 0.052227199 0.2508539 0.060980625
		 0.24375963 0.052172098 0.24279547 0.061402101 0.23599958 0.052348413 0.23496479 0.061218403
		 0.22900367 0.052378748 0.22747767 0.060854975 0.222247 0.052228671 0.22028852 0.061244871
		 0.21465278 0.052518368 0.21265614 0.062241193 0.20634651 0.052914169 0.20494175 0.062604733
		 0.19859588 0.07227575 0.19968861 0.072023436 0.2074371 0.081880428 0.20078087 0.081903368
		 0.19277436 0.091286182 0.19354737 0.091255397 0.20182931 0.081730813 0.20860398 0.091072485
		 0.20991176 0.081430435 0.21623111 0.071223877 0.21553445 0.070855342 0.22305596 0.080965221
		 0.22382152 0.070922367 0.23001677 0.080350496 0.23143768 0.070516683 0.23743421 0.079586841
		 0.23910987 0.069836639 0.24516487 0.090718269 0.21776986 0.10042155 0.19423044 0.10029476
		 0.18548489 0.10900242 0.18558025 0.10866307 0.17631221 0.099963836 0.17658406 0.091184385
		 0.18512571 0.090936273 0.17656803 0.081807606 0.18460792 0.072286315 0.19191003 0.072206676
		 0.18395996 0.062597685 0.1910193 0.05292803 0.19759464 0.062582582 0.18326306 0.072125904
		 0.17585802 0.062679827 0.17535156 0.072112389 0.16765225 0.062839329 0.16731262 0.05351685
		 0.16698039 0.063003711 0.15917337 0.072093636 0.15933329 0.072126023 0.15087456 0.063226953
		 0.15097225 0.054114867 0.15108997 0.053815063 0.15906429 0.054381385 0.14309847 0.063455865
		 0.14272118 0.054801956 0.13505113 0.063749768 0.13441896 0.055305339 0.12685412 0.06419839
		 0.12606341 0.055837698 0.11865473 0.064716324 0.11765283 0.056389138 0.11034924 0.065258443
		 0.10917032 0.056841742 0.10199028 0.065740131 0.10063958 0.057208348 0.093599141
		 0.066154115 0.09199357 0.057423972 0.08511591 0.066474706 0.083253145 0.074486747
		 0.090421021 0.074056059 0.099300563 0.081800669 0.098011136 0.081432141 0.10686135
		 0.073578812 0.10804623 0.081079617 0.11562091 0.073086448 0.11666131 0.08087559 0.12438095
		 0.072661333 0.12525296 0.080827191 0.1331408;
	setAttr ".uvst[0].uvsp[500:749]" 0.072383225 0.13382018 0.080818899 0.14189345
		 0.072242014 0.14236927 0.080897398 0.15063781 0.089597657 0.15012783 0.081116095
		 0.15934008 0.090055145 0.15906191 0.081355117 0.16788566 0.090542406 0.16788417 0.081599712
		 0.17628372 0.099503048 0.1675716 0.098916844 0.15845704 0.10817139 0.16696644 0.10761393
		 0.15760398 0.1162049 0.15662688 0.10704999 0.14830863 0.098306552 0.14932692 0.097791009
		 0.14021802 0.089287855 0.14118767 0.089132331 0.13225865 0.09745644 0.13115329 0.089055538
		 0.12334621 0.09725263 0.12214017 0.089025766 0.11446303 0.097130165 0.11319637 0.089144029
		 0.10561317 0.097073697 0.10431683 0.089354202 0.096750319 0.082168981 0.089017212
		 0.089600272 0.087772429 0.082515143 0.079930365 0.074848242 0.081471741 0.0898652
		 0.078686595 0.097213209 0.086648285 0.09710937 0.095487535 0.10532182 0.094242573
		 0.10534113 0.10298228 0.10544883 0.11182761 0.11416546 0.11038977 0.11440982 0.11935741
		 0.10564832 0.12079334 0.11479767 0.12849039 0.12374137 0.12710917 0.12408368 0.13648432
		 0.13292298 0.1352607 0.13310385 0.14488822 0.14182535 0.14384222 0.14183399 0.153687
		 0.1505121 0.15274996 0.1503827 0.16267979 0.15921202 0.1617074 0.15905832 0.17152262
		 0.16822447 0.17040998 0.16806588 0.18002284 0.17756774 0.17893445 0.17728111 0.18837065
		 0.18690021 0.18756145 0.18637535 0.19692326 0.19579008 0.19675046 0.19503324 0.20610225
		 0.20394537 0.20667857 0.20306891 0.21575105 0.21273755 0.20813704 0.2142819 0.19921046
		 0.20511915 0.19746763 0.21607074 0.18992215 0.20641302 0.18815255 0.19664815 0.18739271
		 0.19738488 0.17806661 0.1873626 0.17820376 0.18771477 0.16877508 0.17781436 0.16944045
		 0.1779941 0.15986204 0.16839033 0.16073442 0.16853632 0.1509918 0.15938447 0.15185052
		 0.15955818 0.14199024 0.1506207 0.14286959 0.15073238 0.13308156 0.14179981 0.13411522
		 0.14179036 0.12454385 0.13274565 0.12578166 0.13259229 0.11650568 0.12342067 0.117908
		 0.12319902 0.10891593 0.11403651 0.10159665 0.12309826 0.10015744 0.11400355 0.09297359
		 0.10536942 0.085579395 0.11404752 0.084491193 0.10546337 0.07693398 0.097397707 0.077720582
		 0.097636849 0.068738639 0.090091504 0.069508493 0.090199545 0.060211897 0.082799725
		 0.051742136 0.090231009 0.050676465 0.090677708 0.041035891 0.098336659 0.050720155
		 0.097926199 0.059726417 0.1061375 0.059648633 0.10570614 0.06827563 0.11436721 0.067857802
		 0.11417284 0.076127291 0.12313564 0.075149119 0.12309282 0.083286226 0.12307657 0.09161514
		 0.13245562 0.09014982 0.13244073 0.098671854 0.13248049 0.10745591 0.14189976 0.10607278
		 0.14182559 0.11518133 0.15106899 0.11400586 0.15087406 0.12344176 0.15999725 0.12251294
		 0.159748 0.13219482 0.16891314 0.13145131 0.16869912 0.1412127 0.17817587 0.14053714
		 0.17810361 0.15021712 0.18805785 0.14967442 0.18794277 0.15925056 0.19830292 0.15911549
		 0.19793655 0.16862869 0.20840077 0.16922104 0.20757803 0.17874008 0.21897461 0.17047507
		 0.21995218 0.16106761 0.20904252 0.15966642 0.22113515 0.15181714 0.20964475 0.15015644
		 0.198539 0.14956033 0.21011645 0.14063686 0.22242945 0.14243537 0.22369084 0.13286543
		 0.21022287 0.13113523 0.19860011 0.14005679 0.19846572 0.13050151 0.20996343 0.12132585
		 0.22462837 0.12314397 0.22487874 0.11224389 0.20953828 0.10841912 0.20410568 0.109375
		 0.19894741 0.11890489 0.19714062 0.11044312 0.19701748 0.10177422 0.18831755 0.10175592
		 0.18864702 0.092570662 0.17958866 0.092951775 0.1792091 0.10217273 0.17031153 0.093689561
		 0.17051353 0.084681332 0.1611657 0.085802019 0.16096756 0.094673276 0.15168291 0.087138057
		 0.1516861 0.078623772 0.14206132 0.080273509 0.14195351 0.072150469 0.13244176 0.073839605
		 0.13247129 0.081877887 0.12319335 0.067202866 0.13236417 0.066082835 0.12336309 0.059348762
		 0.11474075 0.059623063 0.11534024 0.051556885 0.10674495 0.051139474 0.10769879 0.042844176
		 0.099136218 0.041833639 0.10068557 0.033042789 0.091892727 0.031489015 0.095287032
		 0.019043922 0.08667174 0.016727507 0.081382729 0.030141711 0.073041789 0.020577252
		 0.067124307 0.027127206 0.078324348 0.010404408 0.10355502 0.021450043 0.11181824
		 0.02357769 0.10933687 0.034795165 0.11779264 0.036396146 0.12001853 0.025259495 0.12623583
		 0.037640929 0.12455469 0.044364274 0.13188837 0.043996036 0.13209276 0.051030755
		 0.12376308 0.051667273 0.11624251 0.043780386 0.1322501 0.058448613 0.14130765 0.056567788
		 0.14170788 0.064275384 0.15145412 0.070308924 0.15096755 0.062153995 0.16083157 0.068548203
		 0.16115536 0.077090263 0.17046477 0.075787008 0.17975715 0.083811045 0.17950915 0.074775457
		 0.17004658 0.067022204 0.17895396 0.065834045 0.16924772 0.05841434 0.16016154 0.060140908
		 0.15914442 0.051813245 0.15022729 0.054150105 0.14918758 0.046177626 0.14061692 0.048975408
		 0.13934763 0.041858077 0.1315705 0.038637936 0.13633685 0.036333859 0.14772332 0.038341582
		 0.14534406 0.031066716 0.15605232 0.035192192 0.15779366 0.043520451 0.16681236 0.041293919
		 0.16822594 0.049844921 0.17766634 0.048280358 0.1784182 0.05702281 0.18785645 0.055775762
		 0.18807831 0.064812124 0.19755971 0.064004958 0.19738193 0.07369113 0.20640288 0.074219823
		 0.19736068 0.083319545 0.18838017 0.074020803 0.18867166 0.083302498 0.1972422 0.092723906
		 0.2058526 0.084138155 0.2053441 0.093518019 0.20472005 0.10238481 0.20745976 0.063451827
		 0.19771422 0.054481626 0.20835817 0.052048802 0.19726321 0.04522419 0.18737122 0.046928942
		 0.18719627 0.038054883 0.17686191 0.0395028 0.17573097 0.030694604 0.16506976 0.032579243
		 0.17417069 0.02178055 0.18554661 0.020848215 0.18424401 0.0099084973 0.17276199 0.010167897
		 0.16295078 0.023487449 0.1600904 0.011483729 0.15033577 0.016149163 0.15371941 0.026864886
		 0.14159553 0.021685779 0.1302361 0.028991997 0.19412269 0.0096465349 0.19519094 0.020083547
		 0.18667926 0.029314101;
	setAttr ".uvst[0].uvsp[750:999]" 0.19629109 0.027972996 0.19692795 0.036366761
		 0.20555164 0.03381753 0.20663589 0.042434216 0.20407262 0.025942206 0.20283636 0.019214213
		 0.20394969 0.0078312755 0.14205486 0.08861959 0.14199248 0.097221911 0.15152977 0.095863879
		 0.15130939 0.10481346 0.16066174 0.10373724 0.16031854 0.1130175 0.16956602 0.11220866
		 0.16919728 0.12176126 0.17848805 0.12114191 0.17826924 0.13085836 0.1880156 0.1304853
		 0.18807979 0.14009666 0.18801196 0.12056369 0.17881718 0.11154735 0.18802103 0.11102343
		 0.16996695 0.10285288 0.21788481 0.18015856 0.21145052 0.21681476 0.20250702 0.22472072
		 0.19443977 0.21536291 0.19405352 0.22448927 0.18560851 0.21559536 0.18537076 0.22476614
		 0.17664981 0.21643925 0.17680749 0.20715272 0.18593445 0.20629752 0.17702425 0.19775993
		 0.16793771 0.18958396 0.19372906 0.23338598 0.20206054 0.23352325 0.20159657 0.24208724
		 0.20065752 0.25132036 0.20942548 0.2423287 0.20924099 0.25238711 0.22020474 0.24698031
		 0.21932858 0.2539717 0.20840804 0.26150477 0.21799988 0.26293814 0.21623079 0.2722038
		 0.20996852 0.23398173 0.21065322 0.22537404 0.15895732 0.18129122 0.15027545 0.17261785
		 0.14181206 0.16361213 0.13339002 0.16450441 0.13326256 0.15464413 0.12473646 0.15562248
		 0.12441847 0.14599562 0.11574741 0.14715338 0.11527311 0.13777208 0.10648355 0.13904846
		 0.10598005 0.12987065 0.085100122 0.26451993 0.086251065 0.25656009 0.094897822 0.25845081
		 0.096223138 0.2506721 0.10805018 0.22895932 0.20649117 0.30732894 0.19915429 0.30537939
		 0.19361885 0.29549146 0.20434335 0.31510675 0.15925224 0.30832893 0.1969517 0.34266365
		 0.18950519 0.34140861 0.18373527 0.33362627 0.1820288 0.34048295 0.1763425 0.33262908
		 0.19525614 0.34905958 0.17025813 0.38271528 0.18904123 0.37894917 0.17248195 0.39309782
		 0.1760736 0.40413058 0.16545169 0.39571041 0.19075859 0.38952899 0.19350161 0.40107691
		 0.19029123 0.40971625 0.19532816 0.40888214 0.19693467 0.41644466 0.19263299 0.41761458
		 0.13578494 0.39926481 0.13037367 0.3912015 0.12907881 0.39780664 0.12417445 0.39031094
		 0.12492196 0.38346839 0.12550625 0.37506533 0.11908174 0.37489617 0.11850052 0.38317436
		 0.112116 0.38302183 0.1179158 0.38983357 0.11780617 0.39525473 0.12287128 0.39616036
		 0.11174611 0.38991606 0.11178052 0.39601302 0.10521628 0.39637423 0.10539555 0.39004523
		 0.10584542 0.38266969 0.099144056 0.39007568 0.098779954 0.39640033 0.093154311 0.39638793
		 0.093215093 0.38991445 0.087402232 0.39658952 0.087421432 0.38913798 0.093265079
		 0.3807919 0.099633135 0.38202834 0.099568829 0.37307668 0.093169875 0.37206089 0.086410336
		 0.37918884 0.086598136 0.37067366 0.093265533 0.36347312 0.099766731 0.36428761 0.099957131
		 0.35555482 0.10650093 0.35612792 0.10658011 0.34738863 0.11339191 0.34786844 0.11346632
		 0.33939767 0.12038434 0.339984 0.12053759 0.33164644 0.12751706 0.33201993 0.1277937
		 0.3236506 0.13443792 0.33215964 0.13402884 0.34055209 0.14080949 0.34046251 0.14026509
		 0.34876132 0.13360666 0.34888387 0.13963039 0.35719252 0.14541723 0.36540312 0.13307419
		 0.3573736 0.12690848 0.34874701 0.12649734 0.35731578 0.12602009 0.3661108 0.11953161
		 0.36589152 0.11989072 0.35702276 0.11301429 0.36545086 0.11263813 0.37457848 0.10618874
		 0.37397921 0.10640891 0.36491346 0.11322991 0.35657263 0.12016814 0.34838569 0.12723282
		 0.34038877 0.14758641 0.34017199 0.1413949 0.33213079 0.14208619 0.32385588 0.13493779
		 0.3237769 0.13547298 0.31550992 0.12801522 0.31533873 0.12815654 0.30720878 0.12028823
		 0.30698812 0.12051475 0.31509233 0.11297759 0.31457609 0.11333158 0.32275671 0.10595892
		 0.32201517 0.10639653 0.33032775 0.09955395 0.32946849 0.099867158 0.33801961 0.092870072
		 0.33706701 0.092819855 0.34608406 0.085871398 0.34516191 0.086013287 0.35382748 0.079590142
		 0.35231179 0.079516523 0.36060822 0.072166122 0.3579222 0.07147529 0.36568952 0.063035861
		 0.36222589 0.061499007 0.36942124 0.052651741 0.36565059 0.053982403 0.35856235 0.063691705
		 0.35452819 0.043858323 0.3547349 0.04220479 0.36178994 0.035616457 0.35331011 0.034380998
		 0.35973275 0.039185833 0.36838567 0.05009675 0.37229627 0.058964577 0.3762536 0.05557913
		 0.38296193 0.060950179 0.38614678 0.056530122 0.39243829 0.061911963 0.39550138 0.053379837
		 0.39886844 0.04714141 0.39553034 0.051122725 0.38937104 0.042554129 0.38558102 0.046686534
		 0.37935209 0.03532631 0.37486053 0.03188213 0.36602354 0.027509674 0.3716411 0.032368358
		 0.3812623 0.023980515 0.37763846 0.021104133 0.38359243 0.029914705 0.38764322 0.0391463
		 0.39174104 0.027648956 0.39391851 0.018727504 0.38991481 0.017157132 0.39714396 0.025909424
		 0.4005267 0.036610279 0.39813447 0.034633543 0.40471786 0.024902537 0.40826952 0.016283505
		 0.40505707 0.015766941 0.41401434 0.023368748 0.41635096 0.032794721 0.41167337 0.030432293
		 0.41887105 0.020940656 0.42435479 0.02772825 0.42621684 0.025078172 0.43375576 0.034150038
		 0.42795241 0.036930766 0.42119205 0.042515393 0.42326945 0.045416877 0.41721284 0.049283784
		 0.41956544 0.046794459 0.42527366 0.039907228 0.42950857 0.044714116 0.4309777 0.037681241
		 0.435866 0.042977653 0.43647587 0.048989549 0.4326607 0.050530724 0.42772424 0.048184197
		 0.43715179 0.042185932 0.44275039 0.036248107 0.44263685 0.035981245 0.44976676 0.042404626
		 0.44943458 0.048083544 0.4429782 0.048184197 0.4483856 0.043686096 0.4556576 0.036887363
		 0.45688045 0.038753565 0.46373045 0.045596261 0.46156442 0.050014272 0.45372021 0.05221856
		 0.45907331 0.047896434 0.46721888 0.041413419 0.470321 0.044994947 0.47636485 0.050928686
		 0.47248757 0.049813192 0.48139405 0.044244695 0.48637033 0.050966516 0.49108809 0.046554636
		 0.49714863 0.058070507 0.49470305 0.06136461 0.48888826 0.055342715 0.48555768 0.06461896
		 0.48339057;
	setAttr ".uvst[0].uvsp[1000:1173]" 0.070168942 0.48593521 0.072650194 0.48081911
		 0.067980431 0.47780037 0.059482165 0.4803707 0.063302495 0.47479808 0.054819115 0.47674906
		 0.059093632 0.47203934 0.056429807 0.46901214 0.054365482 0.4643532 0.077625893 0.48285115
		 0.076370671 0.48763585 0.067784123 0.49144429 0.074807912 0.49309158 0.065432258
		 0.49733424 0.073193796 0.49892014 0.063290223 0.50361872 0.071781911 0.50501698 0.081137784
		 0.49946302 0.08026462 0.50517148 0.088978618 0.49948263 0.088402636 0.50490487 0.096698239
		 0.49934405 0.096338451 0.50462788 0.10441183 0.49894321 0.10442774 0.50419754 0.11228403
		 0.49745917 0.11282514 0.5027343 0.10502893 0.50906885 0.096517146 0.50955373 0.097133011
		 0.51425868 0.10616954 0.51349002 0.11389349 0.50760496 0.11515393 0.51188022 0.088812187
		 0.51486385 0.088345498 0.51000726 0.079835296 0.51067913 0.079637848 0.51610005 0.070316851
		 0.5170663 0.070698336 0.51124918 0.060584482 0.51685256 0.061584666 0.51029497 0.050194904
		 0.51479143 0.052116431 0.50776547 0.038972031 0.51135087 0.042344414 0.50390875 0.027712461
		 0.50470209 0.032906279 0.4980334 0.054905564 0.5009743 0.038441945 0.49186689 0.024999216
		 0.48992944 0.017654158 0.49583673 0.019550348 0.48013872 0.027223274 0.47658014 0.024214314
		 0.46763206 0.031675592 0.46565461 0.029913457 0.45779586 0.029269427 0.44994438 0.022621449
		 0.45870042 0.022210652 0.4500041 0.015070992 0.45942658 0.016428806 0.4695946 0.0081689944
		 0.47107899 0.011328141 0.48322403 0.0078125 0.45953405 0.014959317 0.44985569 0.008553436
		 0.44941175 0.015966432 0.44081724 0.023033043 0.44164574 0.031640261 0.43492627 0.029852107
		 0.44225168 0.01823434 0.43242639 0.011452879 0.43125182 0.0097285733 0.44011688 0.013995487
		 0.42259121 0.03453346 0.47337425 0.031874519 0.48480278 0.038600314 0.48039079 0.11212908
		 0.49172282 0.10490988 0.49331468 0.11214804 0.48595452 0.10572375 0.48760837 0.098642148
		 0.48823255 0.099693567 0.48324615 0.090773933 0.48851645 0.089878269 0.49392712 0.082242489
		 0.49380422 0.083216541 0.48845053 0.090934001 0.48399305 0.083657339 0.48363245 0.09751188
		 0.49379551 0.10652365 0.48254097 0.11225711 0.4806695 0.052076556 0.4219259 0.055264782
		 0.41625154 0.051772203 0.41405594 0.058110949 0.40979373 0.055385549 0.40795368 0.048183855
		 0.41142273 0.050703857 0.40517557 0.058199897 0.40178442 0.044371136 0.40187329 0.042063579
		 0.4082619 0.039674792 0.41463315 0.060978238 0.40411031 0.066254199 0.4000231 0.068068936
		 0.3901211 0.074238405 0.39726633 0.076565392 0.38581407 0.081290819 0.39659745 0.078178473
		 0.3766582 0.069740415 0.37307727 0.079225011 0.36857873 0.086335927 0.3623485 0.066570014
		 0.38021755 0.07237538 0.34971964 0.079425529 0.34358287 0.093045026 0.35482055 0.085800961
		 0.33588499 0.099945322 0.34682548 0.092565149 0.32846427 0.10661749 0.33874142 0.098723941
		 0.32118177 0.1134711 0.33105409 0.105381 0.31387126 0.12059814 0.32332963 0.11241195
		 0.30655688 0.11995264 0.29908216 0.12824142 0.29935873 0.12832776 0.29185236 0.13649145
		 0.29964459 0.13598625 0.30744267 0.034084145 0.32592565 0.043101937 0.31935412 0.052553471
		 0.32035649 0.051080119 0.31316 0.041928049 0.31257915 0.03330788 0.31920815 0.032694295
		 0.3125965 0.040733144 0.30570138 0.049325936 0.30607224 0.057939176 0.30705595 0.059798326
		 0.31443906 0.066340081 0.30839103 0.07252989 0.30211377 0.032098431 0.30578172 0.031237872
		 0.29861856 0.078714244 0.29563248 0.085281551 0.28906369 0.092486314 0.28215647 0.101297
		 0.27548492 0.11132611 0.269256 0.030145893 0.29117137 0.029179791 0.28335178 0.028528377
		 0.27533221 0.028036689 0.26723319 0.027315862 0.25922382 0.026563 0.25092649 0.026039731
		 0.24262315 0.025657561 0.23441589 0.025566904 0.2265268 0.025346056 0.21895206 0.025021825
		 0.21152067 0.024685325 0.20415503 0.02435655 0.19682986 0.024281457 0.18978906 0.033843983
		 0.18958467 0.024398584 0.18256485 0.034278866 0.18198639 0.037489701 0.054611266
		 0.047516085 0.053944945 0.038057502 0.045591652 0.04815625 0.033737957 0.038185876
		 0.032968819 0.05740568 0.060239017;
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr -s 1174 ".vt";
	setAttr ".vt[0:165]"  17.66855621 57.79174805 -19.084560394 14.6113739 59.1882019 -19.43363953
		 16.92065239 60.30821609 -18.85389328 19.74469948 59.36179352 -18.39284515 20.85115433 57.030838013 -18.69302368
		 22.26191902 57.50569153 -17.92439651 21.95154572 60.33258438 -17.53322983 24.13737869 60.41375732 -16.095249176
		 21.6700325 62.45487213 -17.27375031 19.20489693 61.54814529 -18.17018509 18.92946243 63.91106033 -17.9403801
		 16.55992126 62.94449615 -18.58942413 16.40162277 65.59840393 -18.31469727 14.19119263 64.95778656 -18.79239655
		 14.13095856 67.69084167 -18.50533295 16.3302269 68.24205017 -18.053985596 18.81308365 66.3651886 -17.70981598
		 18.74298859 68.88185883 -17.48642731 21.39291954 67.073364258 -16.90991211 21.32577133 69.51340485 -16.71411896
		 23.98419952 67.62000275 -15.62483215 24.038093567 65.20652771 -15.75653076 26.69950867 65.52623749 -14.28384399
		 26.72940636 68.057144165 -14.21878052 23.95689964 70.047111511 -15.51721191 26.75186539 70.53555298 -14.18070221
		 23.92658424 72.48886871 -15.42298126 26.76292801 72.99976349 -14.16251373 23.93401146 74.93583679 -15.37062073
		 26.77099609 75.47151184 -14.16542053 23.98060036 77.40163422 -15.33809662 26.8111763 77.94789886 -14.17943573
		 24.052524567 79.84438324 -15.31843567 26.86162186 80.36899567 -14.19910431 24.15975952 82.2405777 -15.30538177
		 26.94292068 82.71709442 -14.21472931 24.2608223 84.60532379 -15.27948761 27.0054283142 84.99785614 -14.21942902
		 24.34832382 86.93855286 -15.23921967 27.073635101 87.28244781 -14.20278168 24.40975571 89.27935791 -15.16822052
		 27.1011467 89.56172943 -14.16352844 24.4119091 91.5723114 -15.048942566 27.073059082 91.81089783 -14.10136414
		 24.43367577 93.85292816 -14.91370392 27.054439545 94.039108276 -14.025802612 24.4662075 96.10455322 -14.76010132
		 27.078077316 96.16479492 -13.95491028 24.48556709 98.35150146 -14.58522797 27.10293579 98.33907318 -13.88752747
		 24.5060997 100.60469818 -14.40981293 21.77338028 98.42156982 -15.16869354 21.75156403 100.69236755 -14.92381287
		 24.48725319 102.79208374 -14.28017426 21.69937706 102.91794586 -14.72872162 24.41823196 104.94055939 -14.18626404
		 27.15207481 104.90731812 -13.61307526 27.055620193 107.031402588 -13.56616211 24.34122276 107.087287903 -14.12389374
		 26.94271278 109.20334625 -13.54413605 24.26119423 109.24397278 -14.077377319 26.82701683 111.39981079 -13.52220154
		 24.19273376 111.44304657 -14.038139343 26.73411751 113.53274536 -13.49449921 24.13965988 113.56752014 -14.0018692017
		 26.65325356 115.59870911 -13.4515686 24.088056564 115.6300354 -13.9551239 26.54162407 117.67824554 -13.38651276
		 24.016839981 117.69495392 -13.89839935 26.36384201 119.86541748 -13.29518127 23.90782547 119.86064911 -13.79091644
		 26.16392899 122.024436951 -13.14270782 23.72939301 122.043022156 -13.6003952 25.95948029 124.067985535 -12.92591095
		 23.53018951 124.090278625 -13.32991791 25.72795105 126.08997345 -12.66611481 23.35809708 126.12727356 -13.030532837
		 25.41732979 128.086013794 -12.34855652 23.086679459 128.15786743 -12.70323181 25.025571823 130.04788208 -12.0085144043
		 22.65303993 130.17184448 -12.37217712 24.63203049 131.2653656 -11.79406738 22.15904427 131.58357239 -12.071258545
		 20.24093437 130.49009705 -12.66984558 20.65418434 128.4150238 -12.99864197 18.058759689 128.8167572 -13.38012695
		 17.64191437 130.94421387 -13.074493408 19.70826721 131.95315552 -12.36660767 17.10515213 132.67236328 -12.76344299
		 15.25421429 131.29193115 -13.39505005 15.70941734 129.15144348 -13.66268921 13.38949108 129.53031921 -13.9208374
		 13.6831131 127.43172455 -14.1548233 11.38510132 127.87985229 -14.34711456 11.56497192 125.8705368 -14.53710175
		 9.12693405 126.30448151 -14.63359833 9.08102417 124.33685303 -14.73070526 6.49857616 124.76186371 -14.74852753
		 6.18553543 122.54830933 -14.81736755 3.57674122 122.91833496 -14.82200623 3.2882812 120.6818161 -14.91875458
		 0.95165324 123.13505554 -14.82400513 1.17242205 125.30516815 -14.72852325 -1.53534102 125.27607727 -14.73027039
		 1.022645593 127.16175842 -14.61122131 3.71676183 126.92634583 -14.63677979 3.69240189 128.73149109 -14.54237366
		 6.33396769 128.45735168 -14.53031921 5.91024828 130.35934448 -14.38803101 8.46690273 130.16282654 -14.30075073
		 7.99956036 132.23309326 -14.093963623 10.45449734 131.9724884 -13.9360199 9.98821735 133.98933411 -13.66981506
		 12.34496212 133.63580322 -13.42024231 11.78739834 135.9299469 -13.21638489 14.11449718 135.4627533 -12.88464355
		 13.58892727 137.74716187 -12.69303894 15.97285938 137.14587402 -12.28233337 15.56375885 139.3963623 -12.048187256
		 17.98166466 138.62251282 -11.59680176 17.68746185 140.76367188 -11.28401184 20.18631744 139.71510315 -10.86074829
		 20.041097641 141.5459137 -10.48361206 22.78127098 140.38648987 -9.77709961 23.011358261 138.64541626 -10.23410034
		 25.59643555 139.6499176 -9.20051575 25.38967896 141.22389221 -8.69508362 22.58091736 142.056396484 -9.37442017
		 25.37824821 142.092971802 -8.57211304 22.69343376 143.37840271 -8.87947083 20.010644913 143.27905273 -10.023971558
		 19.99059486 144.95117188 -9.29705811 17.33772659 144.84724426 -10.22979736 17.46346092 142.86607361 -10.85328674
		 14.96435452 144.033325195 -11.24954224 15.26185513 141.67430115 -11.73167419 12.97515965 142.44192505 -12.18069458
		 13.20601749 140.056472778 -12.47468567 10.92605591 140.62187195 -12.7848053 11.26730061 138.2467041 -13.022338867
		 9.074199677 138.6486969 -13.21264648 9.53540039 136.3031311 -13.43649292 7.25501871 136.65751648 -13.60646057
		 7.59296751 134.40104675 -13.85067749 5.20189619 134.61347961 -13.99853516 5.52617693 132.4258728 -14.20729065
		 3.057046652 132.61209106 -14.27229309 3.35623336 130.58377075 -14.42427063 0.85127288 130.73985291 -14.41204834
		 1.022371769 128.91844177 -14.52328491 -1.44905853 129.012588501 -14.53489685 -1.43474793 127.20707703 -14.63139343
		 -3.87337351 128.81439209 -14.54574585 -3.74863386 130.6973114 -14.4443512 -6.3108325 130.58067322 -14.4747467
		 -6.11471128 132.61035156 -14.34469604 -8.52569294 132.52676392 -14.34197998 -8.23539829 134.67893982 -14.16355896
		 -5.94185591 134.76130676 -14.18028259 -7.98607206 136.90104675 -13.93115234 -5.78877115 137.020599365 -13.97608948
		 -7.79125261 139.16191101 -13.59823608 -9.90747166 138.85610962 -13.42002869 -9.6978178 141.10609436 -12.96717834
		 -7.70776033 141.50454712 -13.078460693 -9.55471611 143.34857178 -12.35374451;
	setAttr ".vt[166:331]" -11.51007366 142.99159241 -12.16627502 -11.38731956 145.13690186 -11.47946167
		 -13.31296539 144.72264099 -11.30422974 -13.25235653 146.65472412 -10.59222412 -11.33133698 147.17504883 -10.62927246
		 -9.46064854 145.54064941 -11.60791016 -9.40407944 147.64050293 -10.66145325 -7.51644611 145.98884583 -11.6177063
		 -7.44971657 147.98524475 -10.55284119 -9.40042877 149.72915649 -9.49157715 -11.36712074 149.11218262 -9.63018799
		 -11.44292831 150.93777466 -8.45391846 -13.35342598 150.020050049 -8.60284424 -13.43481827 151.51821899 -7.26046753
		 -15.23925591 150.41799927 -7.49871826 -13.66533184 152.78555298 -5.67025757 -11.43489933 152.84487915 -6.78440857
		 -11.45893192 154.44091797 -4.98022461 -9.36098671 153.74310303 -6.47270203 -9.42367744 151.72891235 -8.1736908
		 -7.40533161 152.157547 -8.15155029 -7.28460693 154.2902832 -6.61038208 -5.44054651 152.37771606 -8.069229126
		 -5.48217487 150.2900238 -9.3625946 -3.53883862 150.36860657 -9.18577576 -3.51642132 152.50939941 -7.9828949
		 -5.256217 154.22080994 -6.55561829 -3.4013586 154.28564453 -6.46325684 -5.10367537 155.4045105 -4.61257935
		 -7.062808514 155.36697388 -4.52435303 -6.45693636 156.035583496 -2.20433044 -7.4478879 155.88012695 -1.58416748
		 -9.49294186 155.44750977 -3.98634338 -9.52716255 155.53314209 0.60473633 -12.092826843 154.88105774 -1.014801025
		 -10.9298563 154.92633057 1.96748352 -12.6229887 154.31378174 1.30760193 -14.52672958 152.96998596 0.52059937
		 -13.41323566 153.2716217 2.93496704 -11.50811481 153.93330383 3.20915222 -11.68979836 153.36288452 4.52429199
		 -13.6584053 152.49986267 4.66722107 -15.12510395 152.23538208 2.70814514 -15.19959164 151.42076111 4.80134583
		 -16.75960922 150.25273132 4.78077698 -16.7323761 151.20175171 2.57151794 -18.15166473 149.37759399 4.76098633
		 -18.32388687 150.30702209 2.46928406 -18.1474514 150.80776978 0.04524231 -19.72220993 150.09236145 0.066009521
		 -19.41960526 150.10310364 -3.41960144 -17.78578758 150.9119873 -3.39555359 -19.059257507 149.37854004 -6.38923645
		 -17.25335884 150.22840881 -6.32197571 -19.078302383 148.58604431 -7.73286438 -17.13764572 149.4336853 -7.72558594
		 -17.18378639 148.13664246 -8.79518127 -15.21269798 149.049758911 -8.73486328 -15.23730183 147.57092285 -9.78683472
		 -13.29840851 148.43652344 -9.79814148 -15.23513126 146.011779785 -10.57606506 -17.24476051 146.72366333 -9.73440552
		 -17.31390762 145.3368988 -10.46632385 -19.33169556 146.14527893 -9.76405334 -19.22428703 147.54386902 -8.87237549
		 -21.2166214 146.89294434 -8.71821594 -20.99648476 147.91731262 -7.5537262 -21.37551498 145.668396 -9.86817932
		 -19.41446114 144.66500854 -10.30265808 -21.57942963 143.89331055 -10.37214661 -19.59892082 143.089614868 -10.64823914
		 -17.45141792 143.73707581 -10.86500549 -15.31855488 144.25350952 -11.093719482 -15.55514812 142.38899231 -11.56434631
		 -13.49386692 142.64837646 -11.91029358 -13.79823685 140.60040283 -12.42095947 -11.72833633 140.82164001 -12.729599
		 -12.029509544 138.62652588 -13.15849304 -10.18453312 136.59899902 -13.71099854 -12.3912077 136.41279602 -13.42060852
		 -14.18633652 138.50080872 -12.80168152 -14.72966385 136.18019104 -13.0089111328 -12.94849777 133.9989624 -13.6399231
		 -15.21944809 133.87242126 -13.33895874 -16.93946838 136.021530151 -12.57295227 -16.3519783 138.37358093 -12.34724426
		 -18.62108612 137.98985291 -11.89572144 -19.12212372 135.85722351 -12.15797424 -20.8079052 138.020233154 -11.39060974
		 -20.36626625 139.91293335 -11.15791321 -22.57450485 139.9621582 -10.75144958 -23.009645462 138.20951843 -10.91592407
		 -21.28650093 135.99209595 -11.6787262 -23.45502853 136.28852844 -11.21722412 -21.7706089 133.92539978 -12.041671753
		 -19.61330986 133.67189026 -12.52078247 -20.11529541 131.45643616 -12.91268921 -17.91456604 131.36766052 -13.34591675
		 -17.43345451 133.69345093 -12.94029236 -15.69886017 131.65306091 -13.70755005 -13.41836548 131.74790955 -13.9539032
		 -13.83073521 130.011459351 -14.22679138 -11.49652958 130.13894653 -14.33258057 -10.88303947 132.0076446533 -14.18115234
		 -8.83706951 130.45942688 -14.47790527 -9.28106403 128.31581116 -14.53166199 -6.53189039 128.63552856 -14.57914734
		 -6.75025415 126.70526123 -14.68670654 -4.037191868 126.95690155 -14.63964081 -4.27602577 125.060317993 -14.75033569
		 -1.71134853 123.14112091 -14.83522797 -4.40773439 122.94854736 -14.86141968 -1.88651752 120.92882538 -14.94536591
		 0.71471512 120.91360474 -14.93096924 0.49962771 118.76589966 -15.054031372 3.029171467 118.55918884 -15.032562256
		 5.86725712 120.31443024 -14.89887238 5.58325005 118.18721008 -14.99655151 2.82523251 116.38187408 -15.14864349
		 5.35340643 116.032203674 -15.096031189 2.68048716 114.14444733 -15.26499176 0.25134152 114.27450562 -15.30187988
		 0.20852995 111.89655304 -15.43688202 -2.15578866 114.22560883 -15.30821991 -2.11097956 116.52604675 -15.18632507
		 0.3487978 116.55356598 -15.17563629 -2.021692753 118.7742691 -15.062919617 -4.55982018 118.56555176 -15.070510864
		 -4.51090765 120.73248291 -14.9629364 -7.14657545 120.40822601 -14.98030853 -7.10636663 122.63963318 -14.8949585
		 -9.70964622 122.26521301 -14.92405701 -9.61893845 124.31555939 -14.80890656 -12.079942703 123.94724274 -14.79615021
		 -11.94822979 126.056289673 -14.67015076 -9.48049927 126.34620667 -14.67776489 -7.0078654289 124.77357483 -14.79737854
		 -11.77721214 128.094345093 -14.51701355 -14.12329102 127.88394165 -14.44551086 -16.092027664 129.92276001 -13.99523926
		 -16.4054451 127.73904419 -14.23077393 -18.3320713 129.90705872 -13.60801697 -18.69663429 127.70516968 -13.88148499
		 -16.64504433 125.568367 -14.45079803 -14.30642605 125.76763153 -14.60805511 -14.4552784 123.59952545 -14.73813629
		 -12.20069599 121.74848938 -14.89583588 -14.61965847 121.36024475 -14.83683777 -12.29092789 119.59381104 -14.97135925
		 -9.75373459 120.0040435791 -14.98599243 -9.73556519 117.76702118 -15.051750183 -7.1368804 118.20516968 -15.068099976
		 -7.10509729 115.94210815 -15.16340637 -4.58021355 116.31337738 -15.17928314 -4.58772898 113.99319458 -15.2984314
		 -2.17249799 111.79642487 -15.44443512 -4.575387 111.52082062 -15.42518616 -2.1451838 109.10689545 -15.59358215
		 0.22080982 109.25190735 -15.58931732 2.61585259 111.82245636 -15.3920517 2.61653042 109.23241425 -15.53591919
		 0.28171492 106.52711487 -15.77487183 2.6614449 106.5787735 -15.71068573 0.38740194 103.72740173 -15.99833679
		 -2.072080851 106.33499146 -15.77725983 -4.53028059 108.80266571 -15.56801605;
	setAttr ".vt[332:497]" -4.45095825 106.014137268 -15.74098206 -6.97615862 108.36726379 -15.51582336
		 -7.035019398 111.088989258 -15.38592529 -7.07197237 113.6095047 -15.26865387 -9.62412071 113.12876892 -15.2170105
		 -9.68028641 115.48526764 -15.12558746 -12.28695488 115.0091552734 -15.063583374 -12.33119202 117.31542206 -15.0089950562
		 -14.88767815 116.91622162 -14.93558502 -14.7766819 119.21737671 -14.91850281 -17.24152374 118.95352936 -14.80452728
		 -17.032245636 121.30545807 -14.74250031 -16.83528519 123.39067078 -14.61351013 -19.23865128 123.62887573 -14.39582825
		 -19.0067539215 125.49625397 -14.16423798 -21.43286514 125.56961823 -13.74167633 -21.028333664 127.79468536 -13.41918182
		 -23.3991642 128.036499023 -12.92170715 -22.83683968 130.23193359 -12.59126282 -25.06712532 130.62982178 -12.037536621
		 -25.7478981 128.43241882 -12.38354492 -23.91945839 125.79447174 -13.27390289 -26.42268944 126.16122437 -12.75892639
		 -24.29193306 123.92406464 -13.52368927 -21.72266579 123.70080566 -14.005355835 -21.95411301 121.27664185 -14.1609726
		 -19.4715519 121.22293091 -14.5256424 -19.71975327 118.7960968 -14.59631348 -17.40975571 116.57389832 -14.8084259
		 -19.90326309 116.36696625 -14.60289764 -17.46100807 114.26262665 -14.83545685 -14.89533043 114.58427429 -14.96995544
		 -14.83901978 112.17717743 -15.029563904 -12.22435951 112.62728882 -15.13607025 -12.15965462 109.99728394 -15.2246933
		 -9.56537819 110.55578613 -15.31712341 -9.50020409 107.83545685 -15.43637848 -6.89438677 105.57749939 -15.67523956
		 -9.41633034 105.056343079 -15.58226013 -12.090854645 107.26815033 -15.33152008 -12.022956848 104.49977875 -15.46112061
		 -9.3275795 102.23355103 -15.75644684 -6.79279566 102.73873901 -15.86555481 -6.69746447 99.85401917 -16.083221436
		 -4.24185944 100.26577759 -16.17715454 -4.14065075 97.33601379 -16.42510223 -1.72057629 97.68041992 -16.48448181
		 -1.84789133 100.60592651 -16.23408508 0.67967737 97.98033142 -16.49699402 0.85551387 95.09677124 -16.74249268
		 3.30877733 95.42343903 -16.71556854 3.090671539 98.24427032 -16.44348145 0.51904905 100.87002563 -16.24279022
		 2.89896464 101.064964294 -16.16831207 -1.96585488 103.50036621 -15.99191284 -4.34860897 103.16886902 -15.94560242
		 2.75547576 103.84663391 -15.9233551 5.20324564 103.87128448 -15.81736755 5.11560631 106.50038147 -15.60919952
		 7.68929529 106.32866669 -15.49018097 7.66073895 108.80188751 -15.33628082 5.081720829 109.072250366 -15.44650269
		 7.69246197 111.21007538 -15.21796417 5.10304165 111.57395172 -15.31588745 7.78588057 113.44489288 -15.11768341
		 10.45649529 113.023544312 -15.018356323 10.5990448 115.13005829 -14.93897247 7.94826555 115.5881424 -15.025413513
		 10.79295731 117.24414825 -14.87213898 8.17160225 117.72175598 -14.94267273 11.036489487 119.37449646 -14.81428528
		 13.63223076 118.91504669 -14.74146271 13.81829548 120.99277496 -14.65573883 16.27062035 120.54994965 -14.52985382
		 16.23633003 122.78460693 -14.3553009 13.92314339 123.21847534 -14.5194397 16.21717262 124.9037323 -14.11097717
		 13.98989391 125.32875061 -14.30506897 15.95101261 127.039268494 -13.92615509 18.29148102 126.719841 -13.66854095
		 18.57519531 124.53839874 -13.87955475 20.88476181 126.31546783 -13.31856537 21.026004791 124.27098846 -13.62427521
		 18.66673851 122.45376587 -14.15206909 21.18008995 122.20103455 -13.90904236 18.78476334 120.22272491 -14.35134125
		 21.36040115 119.98383331 -14.12569427 18.86193275 118.066947937 -14.47190094 21.45060158 117.86802673 -14.24833679
		 18.80199242 116.0092163086 -14.52580261 21.46707535 115.74864197 -14.30718994 18.9156208 114.1362915 -14.57235718
		 21.51755905 113.75832367 -14.34334564 19.08313179 112.30388641 -14.63263702 21.62428284 111.7721405 -14.39667511
		 19.036045074 110.071174622 -14.68990326 21.60402489 109.52522278 -14.44011688 18.81703568 107.61942291 -14.75463104
		 21.55567169 107.25388336 -14.50888062 18.78369141 105.33670807 -14.86319733 15.94526672 105.60084534 -15.065132141
		 15.94340134 107.8837738 -14.93390656 13.12457657 105.85993195 -15.22530365 13.20302582 103.50683594 -15.44237518
		 10.44925308 103.66693115 -15.58074188 10.37120819 106.10327911 -15.36408997 13.090433121 108.16577148 -15.080062866
		 10.34395409 108.48744202 -15.21238708 13.10589409 110.41756439 -14.98382568 16.10356712 110.27558899 -14.85728455
		 16.14300919 112.47410583 -14.79244232 13.17152596 112.62615204 -14.90882111 16.059698105 114.36587524 -14.72575378
		 13.28173447 114.70280457 -14.84132385 16.11408234 116.36135864 -14.67622375 13.43597031 116.79584503 -14.78781891
		 16.24814415 118.41998291 -14.62374878 10.37187576 110.80955505 -15.10593414 7.76846266 103.79811096 -15.70159149
		 7.89954042 101.23166656 -15.97725677 5.34784985 101.18706512 -16.078346252 5.54545784 98.47129059 -16.37734222
		 8.093732834 98.62697601 -16.29510498 10.57180595 101.19807434 -15.86515808 10.74081039 98.69532013 -16.18597412
		 13.32285309 101.11447144 -15.72307587 16.025033951 103.31628418 -15.26944733 16.13885307 100.9881134 -15.53507996
		 18.86504745 103.11237335 -15.041717529 21.61762047 105.093132019 -14.58591461 18.95740891 100.84044647 -15.2797699
		 16.25881958 98.61960602 -15.83921051 19.023897171 98.52577209 -15.55986786 16.36114883 96.22036743 -16.15077972
		 19.075559616 96.17366791 -15.85369873 21.78905296 96.11906433 -15.43115234 19.12409592 93.78855896 -16.12903595
		 16.46346474 93.78455353 -16.44035339 16.54654884 91.3026123 -16.69243622 19.14777374 91.37864685 -16.35494995
		 21.78876495 91.45007324 -15.86141205 21.79399109 93.79634094 -15.67121887 21.78658295 89.09576416 -16.016181946
		 19.16206169 88.94973755 -16.53536987 21.73004723 86.72149658 -16.13546753 19.14823532 86.50246429 -16.67084503
		 21.63656807 84.30141449 -16.20537567 19.08036232 84.037414551 -16.77113342 21.53040886 81.88134003 -16.26161194
		 18.98715782 81.556427 -16.85433197 21.41331482 79.43127441 -16.3032608 18.88178062 79.055145264 -16.91986084
		 21.32656097 76.96764374 -16.35385895 18.7944622 76.54182434 -16.99291992 21.27450752 74.49732208 -16.44586182
		 18.73505974 73.99790955 -17.10757446 21.27272797 72.0031890869 -16.56690216 18.71417809 71.43110657 -17.27781677
		 16.34423828 73.49927521 -17.59926605 16.40090179 76.11128235 -17.45475769 14.16242599 75.69033813 -17.81971741
		 14.2003231 78.29520416 -17.68647003 16.47712708 78.68689728 -17.34506989 14.23519516 80.87496185 -17.56845856
		 16.5606823 81.22606659 -17.25676727 14.2250309 83.45491028 -17.45463562;
	setAttr ".vt[498:663]" 16.62115479 83.75887299 -17.15974426 14.1639576 86.033340454 -17.31603241
		 16.63276863 86.28364563 -17.040344238 14.085660934 88.608284 -17.14775848 16.5971489 88.80101013 -16.88853455
		 13.97470284 91.17662811 -16.92860413 11.42242622 90.96240997 -17.09513855 13.81661987 93.72727966 -16.66415405
		 11.19368362 93.57821655 -16.81891632 13.64963531 96.22724152 -16.36149597 10.95382309 96.15766907 -16.51117706
		 13.48036003 98.68131256 -16.040931702 8.32655525 95.99129486 -16.61348724 8.59578705 93.32652283 -16.92429352
		 5.78806925 95.73530579 -16.67886353 6.048529625 92.99519348 -16.97392273 3.53451204 92.62371826 -16.99564362
		 6.30776691 90.27442932 -17.25488281 8.86901093 90.65428162 -17.20104218 9.11058235 87.98491669 -17.44526672
		 11.60256958 88.3392334 -17.32261658 11.73194122 85.7153244 -17.50935364 9.29426956 85.32345581 -17.64105988
		 11.83306313 83.093925476 -17.65988922 9.43561554 82.67498779 -17.81318665 11.91691208 80.48075867 -17.79666138
		 9.54981995 80.045478821 -17.96446991 11.95545769 77.87671661 -17.93019867 9.64378548 77.43539429 -18.12467957
		 11.96913528 75.27024841 -18.090560913 14.13210869 73.046890259 -18.0032196045 11.97815323 72.63305664 -18.29545593
		 14.11706161 70.38085175 -18.24029541 16.31939507 70.87231445 -17.80788422 11.99058533 69.96946716 -18.56245422
		 9.76550293 72.24803925 -18.54492188 9.71198082 74.84116364 -18.30740356 7.31799698 74.40763855 -18.48648071
		 7.23106337 76.97285461 -18.26834106 7.11962175 79.5714798 -18.08707428 4.5727911 79.065742493 -18.14949799
		 4.4185524 81.69847107 -17.95001221 6.98008776 82.20500946 -17.90568542 4.21988297 84.37817383 -17.74416351
		 1.60462022 83.88237 -17.7734375 1.41543019 86.63211823 -17.53914642 -1.16948318 86.17854309 -17.52684021
		 -1.31408095 89.0016937256 -17.25695801 -3.86472607 88.5982132 -17.22151947 -3.96094704 91.4864502 -16.93840027
		 -6.49835634 91.11190796 -16.87887573 -6.55479336 94.027038574 -16.59835052 -9.13179016 93.63114929 -16.46019745
		 -9.17976761 96.51327515 -16.19019318 -11.85152245 96.066131592 -16.010406494 -11.89888382 98.89217377 -15.79331207
		 -14.66980362 98.44443512 -15.59791565 -14.68062592 101.22212982 -15.43531036 -17.49057961 100.85163116 -15.23074341
		 -17.43324471 103.61116028 -15.12154388 -20.18806267 103.42534637 -14.86191559 -20.065292358 106.18454742 -14.8034668
		 -22.65518761 106.21777344 -14.33983612 -22.49628067 108.89509583 -14.31881714 -25.2106514 106.5112381 -13.81002808
		 -25.56445313 103.86421204 -13.80922699 -22.89952469 103.49359894 -14.3700943 -25.98621941 101.10513306 -13.83024597
		 -23.17856216 100.7361908 -14.42727661 -20.34224892 100.66339874 -14.95293427 -20.4616642 97.91286469 -15.074150085
		 -17.53099251 98.095443726 -15.37448883 -17.5409832 95.322258 -15.56558228 -14.64911652 95.65292358 -15.804039
		 -14.61104584 92.84103394 -16.058448792 -11.8086338 93.22527313 -16.2721405 -11.7618103 90.36834717 -16.57129669
		 -9.090148926 90.73845673 -16.74916077 -9.049795151 87.84618378 -17.052482605 -6.43725538 88.21273041 -17.16864014
		 -6.37874174 85.34172058 -17.46686554 -3.76541758 85.74475098 -17.49964142 -3.67258453 82.9364624 -17.77048492
		 -1.027842999 83.39754486 -17.7758255 -0.8956244 80.67664337 -18.028923035 1.78493619 81.18256378 -17.99118805
		 1.93404269 78.54445648 -18.22076416 4.69218731 76.48492432 -18.36814117 2.046553612 75.97601318 -18.47171783
		 4.78421593 73.95645142 -18.62020874 7.38882017 71.86869049 -18.75045776 4.85591984 71.47286224 -18.91068268
		 7.45093298 69.33924866 -19.057861328 9.80238533 69.63311768 -18.83432007 9.82811737 67.0035400391 -19.14522552
		 12.019943237 67.28101349 -18.85176849 12.089092255 64.55871582 -19.14583588 14.33805275 62.12878036 -19.097263336
		 12.18896675 61.76714706 -19.4510994 12.17701149 58.9439888 -19.79537582 9.82354736 61.72296906 -19.75479126
		 9.84181213 64.36327362 -19.45027924 7.44232941 64.28031921 -19.71139526 7.47335672 66.80664825 -19.38672638
		 4.938241 66.60971832 -19.56025696 4.90587521 69.02570343 -19.2201004 2.28630137 68.65648651 -19.3591156
		 2.21468616 71.035903931 -19.048187256 2.13602376 73.4739151 -18.75409698 -0.6026417 72.95149231 -18.84736633
		 -0.68159151 75.44773102 -18.55938721 -0.77736735 78.022315979 -18.28421783 -3.53003645 77.51635742 -18.30677795
		 -3.59460688 80.18856812 -18.03288269 -6.29775238 79.74134827 -18.013870239 -6.32925987 82.51103973 -17.7335434
		 -8.99741936 82.13018799 -17.63939667 -9.014303207 84.97186279 -17.34630585 -11.69320488 84.63816833 -17.18572235
		 -11.71994591 87.50109863 -16.87848663 -14.48781776 87.17831421 -16.66695404 -14.55434799 90.013687134 -16.35141754
		 -17.45936012 89.71697235 -16.071281433 -17.51570129 92.52505493 -15.7983551 -20.53933144 92.33605957 -15.44068146
		 -20.52797699 95.13368225 -15.24240112 -23.55926704 95.14136505 -14.65466309 -23.42062378 97.95214081 -14.52561188
		 -26.60222244 95.33345795 -13.91028595 -26.76582336 92.54524231 -13.96386719 -23.64038467 92.32214355 -14.79579926
		 -26.99210358 89.79951477 -14.034072876 -23.71159363 89.51785278 -14.9646759 -20.51406479 89.52990723 -15.67651367
		 -23.74766922 86.71498871 -15.17506409 -27.24669647 87.012718201 -14.11882019 -27.48357964 84.17041016 -14.21798706
		 -23.67987633 83.92580414 -15.43410492 -20.43820572 86.74249268 -15.93498993 -20.30832672 83.94580078 -16.23690033
		 -23.50535774 81.055679321 -15.75361633 -27.61196136 81.28822327 -14.33026886 -27.49131393 78.071754456 -14.4541626
		 -23.23565865 77.28244781 -16.19237518 -21.77334976 77.68666077 -16.7746048 -20.34398842 80.54441833 -16.61292267
		 -19.75268936 78.098777771 -17.024116516 -19.64515686 75.56541443 -17.37208557 -17.10576057 75.6856308 -17.70089722
		 -17.11959457 72.99458313 -18.04460907 -14.47110367 73.23032379 -18.2982254 -14.44426346 75.93222809 -17.95855713
		 -11.75517464 73.56217957 -18.44917297 -11.72883224 70.92534637 -18.78980255 -8.99333954 71.3637619 -18.86884308
		 -9.020536423 73.9614563 -18.54193878 -6.22013998 71.86215973 -18.89801788 -6.13654613 69.37174988 -19.21897888
		 -3.32479668 69.95881653 -19.1926651 -3.20999908 67.58570862 -19.51274109 -0.43280911 68.18148804 -19.46237183
		 -0.52427936 70.53131104 -19.15261841 2.35454035 66.33815002 -19.70383453 -0.32794166 65.91995239 -19.80239868
		 2.39241266 64.052978516 -20.095367432 4.92024708 64.20323181 -19.91027069;
	setAttr ".vt[664:829]" 4.83401012 61.83841705 -20.21657944 7.35919714 61.78375244 -20.010875702
		 7.17474651 59.34622574 -20.30637741 9.6948185 59.11523438 -20.074329376 9.35131264 56.53318405 -20.44691849
		 11.94758987 56.14654541 -20.20522308 11.11819077 52.48435593 -20.80172348 13.68571663 51.88689423 -20.64923859
		 15.041055679 55.83548737 -19.85572052 17.62209702 53.12643433 -19.94743347 19.24431038 55.067855835 -19.30480957
		 16.21347809 50.10900879 -20.53960419 8.65593529 53.12044525 -20.96224976 6.19393444 53.66823578 -21.041740417
		 6.79043102 56.97720718 -20.62974167 4.28595066 57.37570953 -20.76625061 3.75548124 54.082515717 -21.066257477
		 1.78777575 57.66815186 -20.88627625 2.20723438 59.65496063 -20.65013123 0.052867055 59.48109436 -20.76411438
		 -0.084952831 61.53948212 -20.51212311 2.35931587 61.8022995 -20.39345169 4.65644741 59.55244446 -20.49207306
		 -0.21233582 63.70309067 -20.1919136 -2.85607338 63.047149658 -20.19190979 -3.055433273 65.28954315 -19.84542847
		 -5.9838419 66.94330597 -19.54193115 -5.75626373 64.56601715 -19.87106323 -8.7231617 66.32204437 -19.53153229
		 -8.9044075 68.81583405 -19.19815826 -11.62765312 68.32502747 -19.13244629 -14.43467903 70.55556488 -18.65021515
		 -14.27394104 67.91595459 -19.0012512207 -11.41676331 65.76646423 -19.47081757 -14.021043777 65.30656433 -19.34438324
		 -11.093309402 63.25733948 -19.79891968 -8.43949318 63.87157822 -19.86076736 -8.052722931 61.44746399 -20.17963791
		 -5.45429897 62.23653793 -20.19969559 -5.063292027 59.91753006 -20.51092148 -2.57148743 60.83824158 -20.51233673
		 -2.12077427 58.7705307 -20.78733444 0.20586991 57.91229248 -20.93058014 -1.17390609 57.18625259 -20.99721909
		 -4.54825592 57.64170837 -20.80552673 -3.77133417 55.54306793 -21.10710144 -6.9646306 56.61764908 -20.78248978
		 -7.56656694 59.035774231 -20.48294449 -10.1946907 58.27212524 -20.40831757 -10.70259285 60.76081085 -20.11357117
		 -13.46051598 60.18363571 -19.99067307 -13.77345085 62.73448563 -19.67595291 -16.52592278 62.23886108 -19.443367
		 -16.68039894 64.87824249 -19.088409424 -19.4216938 64.48648071 -18.64131927 -19.47646141 67.33026886 -18.34369659
		 -22.10193634 67.33826447 -17.88587189 -19.57198334 70.15493011 -18.034057617 -16.86057663 67.56820679 -18.73336792
		 -17.037876129 70.28128815 -18.38553619 -19.62940216 72.9129715 -17.70907593 -22.054208755 70.26351166 -17.64152527
		 -22.00045585632 73.024581909 -17.35394287 -21.89682961 75.63127899 -17.037406921
		 -22.26093864 64.14807892 -18.029518127 -19.3600502 61.69171143 -18.93279266 -22.37099838 60.77787018 -18.24944305
		 -19.13837242 58.99220276 -19.30862427 -16.29143715 59.65545654 -19.76908493 -16.1476078 57.060211182 -20.085128784
		 -13.1294632 57.62095261 -20.28305435 -12.70267105 55.054512024 -20.58796692 -9.58818817 55.73986816 -20.71328735
		 -12.15316582 52.46977997 -20.963974 -15.48724937 52.051940918 -20.76838684 -14.99736786 48.87770844 -21.2599411
		 -11.6231041 49.099933624 -21.47883224 -8.87152481 53.11016846 -21.10412216 -7.91069746 49.64894104 -21.68563843
		 -5.084143162 51.12375259 -21.59589767 -6.19211054 54.21348572 -21.14054108 -2.56502914 52.83218002 -21.38161087
		 0.70370525 55.087837219 -21.1158371 -17.89015961 48.66186905 -20.96500015 -18.30252457 51.69031143 -20.48011398
		 -15.90400124 54.508564 -20.39894485 -18.69964218 53.97574615 -20.10308456 -18.96347618 56.41500092 -19.71626282
		 -21.41381454 55.5108223 -19.25755692 -21.79236984 58.00049209595 -18.77259445 -20.91689682 53.23973465 -19.69474411
		 -20.47942543 51.28948212 -19.98092651 -20.60100555 47.91935349 -20.077922821 -3.40642309 72.4012146 -18.88723755
		 -3.4722333 74.92079926 -18.58744049 -6.26023769 74.41870117 -18.59204865 -6.2812047 77.043212891 -18.29512787
		 -9.01672554 76.61922455 -18.2309494 -9.0030632019 79.3425827 -17.93100739 -11.70804787 78.99196625 -17.80091858
		 -11.68748474 81.7950592 -17.4909668 -14.40352058 81.49407196 -17.30329132 -14.42750549 84.34277344 -16.98513794
		 -17.26994324 84.097381592 -16.68078613 -17.37654305 86.91096497 -16.36472321 -17.18060303 81.19327545 -17.024459839
		 -14.41394043 78.68074799 -17.62902069 -17.10046387 78.40119934 -17.3671875 -11.73930931 76.24740601 -18.11713409
		 -26.40553665 98.20333099 -13.87004852 -24.9301033 109.078559875 -13.82707977 -22.42736626 111.5351181 -14.29891205
		 -19.98692322 108.91352081 -14.74167633 -19.96709251 111.5987854 -14.68132782 -17.40130997 109.11179352 -14.95451355
		 -17.42617798 111.81103516 -14.88643646 -14.78287125 109.4885788 -15.10384369 -14.73392677 106.75380707 -15.19834137
		 -17.40099907 106.3735733 -15.031867981 -14.70121384 103.98735046 -15.30716705 -11.95662117 101.70518494 -15.61164856
		 -19.96652603 114.031333923 -14.62596893 -22.39196205 113.94119263 -14.27090454 -22.35444641 116.19342041 -14.25604248
		 -22.18637848 118.67159271 -14.23711395 -24.6137619 116.23567963 -13.89125824 -24.68473434 118.81235504 -13.78064728
		 -27.73740578 117.20484924 -13.059951782 -27.58769798 119.20113373 -13.090660095 -24.55337143 121.18154144 -13.68128204
		 -27.34019089 121.40900421 -13.079536438 -26.94337082 123.79425049 -12.99223328 -24.6877327 113.99502563 -13.87497711
		 -24.79323387 111.60214996 -13.85132599 -9.24524879 99.38459778 -15.95812225 -6.61888599 96.94616699 -16.33244324
		 -4.050696373 94.40148926 -16.679245 -1.58870912 94.7575531 -16.72264862 -1.45453572 91.86282349 -16.98005676
		 1.038814664 92.24185181 -17.0054016113 1.22592449 89.42070007 -17.28440857 3.76255488 89.84881592 -17.2702179
		 3.99250269 87.1000061 -17.52436066 6.56462288 87.56149292 -17.50228882 6.79931641 84.87038422 -17.72169495
		 11.58715439 123.70157623 -14.6375351 11.32171249 121.57511902 -14.75234985 8.76761246 122.080673218 -14.79969788
		 8.45058632 119.85475922 -14.86617279 5.19096231 113.84564972 -15.20265961 -24.46185112 132.06741333 -11.88679504
		 -22.28211594 131.74464417 -12.37420654 -20.58031654 129.98908997 -13.12246704 -23.89716911 134.271698 -11.6000824
		 -10.49280643 134.27841187 -13.96742249 -22.093816757 141.50614929 -10.60609436 -19.88592529 141.57691956 -10.9309082
		 -18.079818726 140.17713928 -11.65678406 -17.70691872 142.032516479 -11.25454712 -15.91712761 140.44236755 -12.020812988
		 -21.77277374 142.83782959 -10.37588501 -15.50484943 151.40380859 -5.99557495 -20.85327148 148.79620361 -6.25376892
		 -15.9454565 152.014297485 -3.096084595 -16.38105392 151.74375916 0.16903687 -14.047623634 153.49502563 -2.67982483;
	setAttr ".vt[830:995]" -21.069917679 149.37005615 -3.25177002 -21.2367382 149.38800049 0.19854736
		 -19.75374794 149.60281372 2.44833374 -21.083961487 148.90800476 2.49653625 -20.78291512 148.30143738 4.66661072
		 -19.53119469 148.73291016 4.69883728 -4.75654125 155.98396301 -2.75914001 -3.21848154 155.33853149 -4.77978516
		 -2.85611606 155.93818665 -3.14097595 -1.40518665 155.33624268 -4.99211121 -1.53266716 154.27911377 -6.42695618
		 -1.60242641 152.50866699 -7.84750366 0.37802806 152.52294922 -7.80158997 0.37609643 154.29833984 -6.44335938
		 2.2688396 154.30271912 -6.38433838 0.42239404 155.37127686 -5.097976685 0.35489798 155.98321533 -3.90281677
		 -1.08671093 155.95996094 -3.61875916 2.21176004 155.34310913 -4.95687866 2.032498598 155.90368652 -3.51620483
		 3.88361645 155.88468933 -3.27064514 4.045072556 155.33131409 -4.80070496 4.13684273 154.25074768 -6.3503418
		 5.8581357 155.39672852 -4.70133972 5.686975 155.90130615 -3.095245361 7.2310791 155.83609009 -2.84577942
		 7.57978106 155.35429382 -4.52682495 8.67747307 155.46511841 -2.32496643 9.66173935 155.41346741 -4.27313232
		 8.18216515 154.42948914 -6.6083374 6.00015163422 154.23965454 -6.44445801 6.37723112 152.576828 -8.061981201
		 8.3945322 152.41384888 -8.16986084 10.39337444 153.77909851 -6.4942627 10.46583271 151.95500183 -8.17425537
		 8.42614937 150.35713196 -9.50248718 6.4198885 150.48242188 -9.38339233 6.41212463 148.3296051 -10.55897522
		 4.43083048 148.53088379 -10.39768982 4.47678661 146.22683716 -11.4382019 2.42666006 146.23573303 -11.2414093
		 2.47434545 144.0069732666 -12.19749451 0.42068541 144.10360718 -12.16532898 0.44978064 141.87055969 -13.00090026855
		 -1.58549917 141.90649414 -13.051300049 -1.50213158 139.54406738 -13.58175659 -3.58937216 141.83995056 -13.12068176
		 -3.57512808 144.12799072 -12.37486267 -5.59320259 144.0043334961 -12.44761658 -5.55139923 146.19769287 -11.53071594
		 -3.56687331 146.30036926 -11.39041138 -5.50470591 148.35726929 -10.48165894 -7.43601274 150.084396362 -9.46035767
		 -3.54518962 148.46965027 -10.31452942 -1.58712173 146.33724976 -11.24769592 -1.56859982 148.51486206 -10.18060303
		 -1.59423399 150.35623169 -9.0019226074 0.38525444 150.37385559 -8.94589233 0.39761537 148.52601624 -10.13044739
		 2.36271191 150.42581177 -9.012130737 2.33563519 152.57920837 -7.79647827 4.31913805 152.58329773 -7.8571167
		 4.3848753 150.4637146 -9.16801453 2.39484978 148.51013184 -10.20201111 0.40443763 146.29512024 -11.18457031
		 -1.58767378 144.16072083 -12.24082947 -7.60241127 143.78048706 -12.43159485 -5.6467452 141.70072937 -13.12324524
		 -5.66830969 139.3237915 -13.6413269 -3.60330725 139.46865845 -13.60791016 -3.55853319 137.068405151 -13.94085693
		 -1.35216558 137.14707947 -13.9125061 -1.23509121 134.80949402 -14.11244202 0.54803407 134.91371155 -14.114151
		 0.44619668 137.21266174 -13.89724731 2.6595273 137.089553833 -13.86280823 2.63408685 139.44021606 -13.50177002
		 4.75429583 139.22259521 -13.43544006 4.64878273 141.58854675 -12.97789001 6.70564556 141.37051392 -12.94914246
		 6.56719875 143.77716064 -12.46632385 8.66595173 143.44952393 -12.52052307 8.64022255 145.91418457 -11.74043274
		 10.76055336 145.62846375 -11.73747253 10.68263721 147.85861206 -10.72454834 12.630826 147.28045654 -10.66033936
		 12.67400742 149.24232483 -9.61152649 14.85902023 148.10620117 -9.50337219 15.13727379 149.61505127 -8.36669922
		 17.62001991 148.018417358 -8.35542297 18.045171738 149.24980164 -6.9657135 20.59690094 147.595047 -6.95443726
		 20.23485184 146.37420654 -8.28500366 17.35593987 146.60879517 -9.38781738 23.05122757 144.42919922 -8.080307007
		 23.34031487 145.76428223 -6.51298523 25.18617249 143.37008667 -7.35041809 25.27553749 144.46813965 -5.90757751
		 23.7548542 146.50317383 -4.60519409 21.01943779 148.51872253 -5.13380432 18.56612015 150.10594177 -5.22479248
		 18.96526718 150.55218506 -3.073242188 17.25902367 151.35163879 -2.80903625 17.61889267 151.11405945 -0.60073853
		 16.12163162 152.29875183 -0.35224915 17.477211 150.89581299 1.50624084 19.28465271 149.81611633 1.37294006
		 19.23580742 150.23286438 -0.76931763 21.49411201 148.67472839 -0.66201782 21.26633072 148.8768158 -2.85740662
		 24.12535858 146.73709106 -2.46464539 25.62928772 145.27256775 -4.22322083 26.28602409 145.50868225 -2.2984314
		 24.21831512 146.95391846 -0.42834473 26.56977844 145.66213989 -0.30618286 26.44234276 145.4364624 1.59843445
		 24.094806671 147.061660767 1.5643158 21.50453568 148.46833801 1.40522766 23.7395134 146.86857605 3.48648071
		 26.15155602 145.29115295 3.53556824 25.21954727 144.72003174 5.38824463 22.95525742 146.30326843 5.25331116
		 21.16276932 148.19978333 3.37747192 20.4931469 147.71594238 5.21514893 21.65519333 145.54554749 6.98924255
		 23.83443642 143.91558838 7.069412231 22.062141418 142.92195129 8.72874451 20.24671745 144.43899536 8.60908508
		 19.53017426 146.93121338 6.92372131 18.42963791 145.76431274 8.48562622 18.87880325 142.96813965 10.040237427
		 17.2464962 144.36244202 9.90766907 15.90759754 142.89945984 11.22763062 15.65450859 145.73654175 9.82318115
		 16.72125053 147.035720825 8.42709351 15.12858009 148.19985962 8.45793152 15.96109581 149.36177063 7.042114258
		 14.67743492 150.037567139 7.1963501 13.79561901 148.95140076 8.4551239 14.12403488 147.034347534 9.78851318
		 12.84126663 148.031234741 9.7273407 12.90410137 145.94877625 11.035675049 11.7679472 147.26416016 10.95498657
		 11.62242508 148.82884216 9.64425659 12.43693829 149.36038208 8.3809967 10.57743168 148.34024048 10.56509399
		 9.90692139 146.60736084 11.93862915 11.26846027 145.013290405 12.17285156 9.056460381 144.43161011 13.24336243
		 8.027435303 145.98271179 12.81700134 8.78498554 147.9596405 11.54656982 7.30775404 147.44624329 12.32489014
		 6.22565079 145.57577515 13.55892944 7.080875874 143.90368652 14.2038269 5.081858635 143.54190063 15.011428833
		 4.44581366 145.31524658 14.1975708 5.62385988 147.22192383 12.83023071 3.92316318 147.070617676 13.32798767
		 2.65610027 145.096939087 14.63426208 2.9880414 143.25852966 15.48683929 0.88204134 143.20141602 15.71836853
		 0.84078574 145.018966675 14.81687927 -1.57651293 143.41888428 15.57167816 -1.74541533 141.46450806 16.38114929
		 -4.090477467 142.0050201416 15.81639862 -4.71340704 140.061691284 16.39273834;
	setAttr ".vt[996:1161]" -6.25240421 142.73872375 15.052482605 -5.48995113 144.41085815 14.51727295
		 -3.58135438 143.82081604 15.1288147 -4.78610516 145.99008179 13.92205811 -6.44897175 146.60653687 13.32647705
		 -5.68614006 147.97412109 12.83604431 -4.063556194 147.56871033 13.21554565 -3.10846615 145.49604797 14.39044189
		 -2.47644949 147.13941956 13.58531189 -1.38840044 145.16377258 14.71424866 -1.055617571 146.74514771 13.88334656
		 0.77368468 146.65934753 13.94622803 2.26073718 146.86778259 13.73867798 -7.17390823 148.50183105 12.19598389
		 -8.05044651 147.38803101 12.44044495 -7.30801535 145.14616394 13.72984314 -9.072897911 146.032241821 12.66859436
		 -8.25666046 143.6025238 14.091033936 -10.1837225 144.55683899 12.87348938 -9.35613155 141.98791504 14.39531708
		 -11.7626276 142.89059448 13.0021820068 -12.21451855 145.51815796 11.44264221 -13.54281807 144.13279724 11.50611877
		 -13.69527245 146.71142578 9.96711731 -14.97835827 145.49339294 10.040435791 -14.98534203 147.92532349 8.43692017
		 -16.31060219 146.79083252 8.50495911 -16.087900162 149.1124115 6.77279663 -17.43570328 148.097824097 6.81315613
		 -16.75960922 150.25273132 4.78077698 -18.15166473 149.37759399 4.76098633 -18.74289513 147.32336426 6.8034668
		 -17.58408737 145.87646484 8.52175903 -18.83736801 145.14353943 8.52467346 -19.95538139 146.67953491 6.63813782
		 -19.53119469 148.73291016 4.69883728 -20.78291512 148.30143738 4.66661072 -17.62469673 143.51547241 9.93222046
		 -16.35767174 144.38095093 9.99684143 -15.082616806 142.74278259 11.44262695 -16.38782501 141.58322144 11.41891479
		 -15.02995491 139.7074585 12.94288635 -13.20430851 141.29957581 13.041046143 -12.58472919 138.59541321 14.72264862
		 -10.6185751 140.37956238 14.62379456 -9.53813267 137.57669067 16.20165253 -8.23597431 139.23878479 15.93687439
		 -6.68468237 136.039352417 17.31912231 -5.54031801 138.027770996 16.89608765 -3.10055804 134.84039307 17.95581055
		 -2.45386314 137.081970215 17.50322723 -7.14574242 140.9985199 15.52104187 -1.99262595 139.30754089 16.99324799
		 0.91290563 136.69017029 17.69085693 0.7190842 134.12347412 18.2919693 4.22857428 136.91653442 17.45801544
		 3.8050859 139.14990234 16.76576996 6.4902668 139.63128662 16.014404297 5.76179934 141.63557434 15.53619385
		 7.99002695 142.14854431 14.63140106 10.12354469 142.80105591 13.5838623 8.94574165 140.30395508 14.99372101
		 11.26598072 141.051635742 13.83244324 9.99358845 138.39512634 15.29460907 7.29537153 137.57362366 16.52950287
		 8.29573059 135.44715881 16.97093964 4.84337282 134.58076477 17.96403503 11.13373947 136.58540344 15.46063995
		 13.1081953 138.91674805 13.93782043 14.88295746 136.89376831 13.89403534 15.81339645 139.7663269 12.57022095
		 13.94698048 141.75671387 12.55299377 14.25370121 144.51882935 11.15202332 12.53561974 143.45500183 12.39842224
		 17.45967865 141.34490967 11.3441925 18.89706039 139.79899597 11.41700745 17.046888351 138.25387573 12.60986328
		 20.47931671 141.51530457 10.16505432 3.3857491 141.28585815 16.19661713 1.0046333075 139.018157959 17.093276978
		 0.9656803 141.21563721 16.53205872 -15.19959164 151.42076111 4.80134583 -14.79825306 150.24597168 6.584198
		 -13.6584053 152.49986267 4.66722107 -13.19260025 151.61097717 6.39784241 -12.48212242 150.35899353 7.92205811
		 -10.77171135 151.74220276 7.73078918 -11.19693851 149.20526123 9.61347961 -12.44980907 147.98065186 9.80479431
		 -10.96934509 146.8891449 11.30279541 -9.63122559 148.26863098 11.20031738 -9.57055664 150.50392151 9.70021057
		 -8.24249458 149.61631775 11.2648468 -13.72130871 149.14355469 8.24383545 -11.67830944 152.67724609 6.11219788
		 -11.68979836 153.36288452 4.52429199 13.55961418 150.26435852 7.23521423 13.99155521 151.487854 5.84451294
		 15.38958263 150.82310486 5.67170715 14.60975361 151.91416931 3.82844543 15.59315395 151.58825684 3.74497986
		 16.61730957 150.24151611 5.44613647 17.14743996 150.67526245 3.521698 15.96758747 151.81842041 1.74363708
		 18.97778702 149.51481628 3.3818512 18.39774704 149.033935547 5.25154114 17.62805748 148.20661926 6.92156982
		 14.95166588 152.29212952 1.9954071 14.64096642 153.41203308 0.44065857 15.20468712 152.85223389 -2.47903442
		 12.92203712 154.45275879 -1.10966492 13.23254204 153.68455505 -4.42771912 10.88775158 155.36482239 -1.75621033
		 13.11455441 152.35873413 -6.7587738 15.61964798 150.80967712 -6.86357117 12.80351448 150.90872192 -8.36166382
		 10.58481407 149.96214294 -9.63893127 16.27888489 151.53167725 -4.96281433 14.77172565 146.24623108 -10.51269531
		 12.69797039 145.059967041 -11.58529663 8.52725315 148.20227051 -10.65525818 10.80866814 143.089523315 -12.4768219
		 6.48523474 146.18017578 -11.63922119 8.77568245 141.0098114014 -12.90467834 4.52943373 143.90437317 -12.31829834
		 6.93373394 138.9956665 -13.34294128 2.53226209 141.7600708 -12.99911499 4.94511032 136.89173889 -13.75338745
		 0.50688881 139.55265808 -13.54647827 2.8374548 134.79864502 -14.092544556 0.66582781 132.73512268 -14.27058411
		 -1.53629375 132.83201599 -14.29066467 -1.48361862 130.85844421 -14.43109131 -3.66661644 132.68795776 -14.30807495
		 -3.6152916 134.82815552 -14.14726257 25.91270828 138.032867432 -9.76940918 23.32050133 136.83183289 -10.60844421
		 20.58205986 137.67921448 -11.092483521 21.038061142 135.55960083 -11.33943176 23.71098137 135.069396973 -10.93696594
		 26.1823101 136.42967224 -10.14533997 26.41744804 134.81483459 -10.54264832 24.13365173 133.27616882 -11.34844971
		 21.60954285 133.58634949 -11.64710999 19.098834991 134.16091919 -12.023574829 18.4007988 136.46908569 -11.82858276
		 16.50987244 134.91172791 -12.4947052 14.69945717 133.18565369 -13.11044312 26.70261765 133.0625 -11.048278809
		 27.035114288 131.19728088 -11.47364807 12.88014317 131.6451416 -13.69139099 10.97749424 129.91342163 -14.14245605
		 9.028944969 128.29150391 -14.47036743 6.37160206 126.57991791 -14.66202545 3.84829974 125.10074615 -14.73978424
		 27.37313652 130.073242188 -11.58493042 27.73724937 128.12664795 -11.90579224 28.008392334 126.13584137 -12.19657135
		 28.22616005 124.14285278 -12.42341614 28.50367355 122.17045593 -12.57913208 28.79838371 119.99230957 -12.66629028
		 29.008140564 117.78622437 -12.72219849 29.17681313 115.66482544 -12.76292419 29.25937271 113.57158661 -12.79117584
		 29.37710762 111.46960449 -12.79533386 29.52424622 109.28713226 -12.78974915;
	setAttr ".vt[1162:1173]" 29.67038727 107.12113953 -12.78127289 29.80737114 104.96456146 -12.77137756
		 29.85798645 102.8892746 -12.75995636 27.19573784 102.81101227 -13.66786194 29.839077 100.75816345 -12.75225067
		 27.14710236 100.57720947 -13.83670807 26.64717865 62.94643784 -14.36802292 24.12893486 62.82247162 -15.9199295
		 26.41898918 60.27193451 -14.46399689 23.95051575 56.88531113 -16.38910294 26.28283501 56.54561615 -14.60877228
		 21.4891758 64.71152496 -17.084976196;
	setAttr -s 3329 ".ed";
	setAttr ".ed[0:165]"  0 1 1 1 2 1 2 0 1 2 3 1 3 0 1 4 0 1 3 4 1 3 5 1 5 4 0
		 3 6 1 6 5 1 6 7 1 7 5 1 8 7 1 6 8 1 6 9 1 9 8 1 10 8 1 9 10 1 9 11 1 11 10 1 12 10 1
		 11 12 1 11 13 1 13 12 1 13 14 1 14 12 1 14 15 1 15 12 1 16 12 1 15 16 1 15 17 1 17 16 1
		 18 16 1 17 18 1 17 19 1 19 18 1 19 20 1 20 18 1 21 18 1 20 21 1 20 22 1 22 21 1 20 23 1
		 23 22 0 20 24 1 24 23 1 24 25 1 25 23 0 24 26 1 26 25 1 26 27 1 27 25 0 26 28 1 28 27 1
		 28 29 1 29 27 0 28 30 1 30 29 1 30 31 1 31 29 0 30 32 1 32 31 1 32 33 1 33 31 0 32 34 1
		 34 33 1 34 35 1 35 33 0 34 36 1 36 35 1 36 37 1 37 35 0 36 38 1 38 37 1 38 39 1 39 37 0
		 38 40 1 40 39 1 40 41 1 41 39 0 40 42 1 42 41 1 42 43 1 43 41 0 42 44 1 44 43 1 44 45 1
		 45 43 0 44 46 1 46 45 1 46 47 1 47 45 0 46 48 1 48 47 1 48 49 1 49 47 0 50 49 1 48 50 1
		 48 51 1 51 50 1 51 52 1 52 50 1 52 53 1 53 50 1 52 54 1 54 53 1 54 55 1 55 53 1 56 53 1
		 55 56 1 55 57 1 57 56 1 55 58 1 58 57 1 58 59 1 59 57 1 58 60 1 60 59 1 60 61 1 61 59 1
		 60 62 1 62 61 1 62 63 1 63 61 1 62 64 1 64 63 1 64 65 1 65 63 1 64 66 1 66 65 1 66 67 1
		 67 65 1 66 68 1 68 67 1 68 69 1 69 67 1 68 70 1 70 69 1 70 71 1 71 69 1 70 72 1 72 71 1
		 72 73 1 73 71 1 72 74 1 74 73 1 74 75 1 75 73 1 74 76 1 76 75 1 76 77 1 77 75 1 76 78 1
		 78 77 1 78 79 1 79 77 1 78 80 1 80 79 1 80 81 1 81 79 1 82 81 1 80 82 1 83 82 1 80 83 1
		 80 84 1;
	setAttr ".ed[166:331]" 84 83 1 84 85 1 85 83 1 85 86 1 86 83 1 86 87 1 87 83 1
		 88 87 1 86 88 1 89 88 1 86 89 1 86 90 1 90 89 1 91 89 1 90 91 1 90 92 1 92 91 1 93 91 1
		 92 93 1 92 94 1 94 93 1 95 93 1 94 95 1 94 96 1 96 95 1 97 95 1 96 97 1 96 98 1 98 97 1
		 99 97 1 98 99 1 98 100 1 100 99 1 100 101 1 101 99 1 102 99 1 101 102 1 101 103 1
		 103 102 1 103 104 1 104 102 1 105 102 1 104 105 1 104 106 1 106 105 1 107 105 1 106 107 1
		 106 108 1 108 107 1 109 107 1 108 109 1 108 110 1 110 109 1 111 109 1 110 111 1 110 112 1
		 112 111 1 113 111 1 112 113 1 112 114 1 114 113 1 115 113 1 114 115 1 114 116 1 116 115 1
		 117 115 1 116 117 1 116 118 1 118 117 1 119 117 1 118 119 1 118 120 1 120 119 1 121 119 1
		 120 121 1 120 122 1 122 121 1 122 123 1 123 121 1 124 121 1 123 124 1 125 124 1 123 125 1
		 123 126 1 126 125 0 123 127 1 127 126 1 127 128 1 128 126 0 127 129 1 129 128 1 127 130 1
		 130 129 1 131 129 1 130 131 1 132 131 1 130 132 1 130 133 1 133 132 1 134 132 1 133 134 1
		 133 135 1 135 134 1 136 134 1 135 136 1 135 137 1 137 136 1 138 136 1 137 138 1 137 139 1
		 139 138 1 140 138 1 139 140 1 139 141 1 141 140 1 142 140 1 141 142 1 141 143 1 143 142 1
		 144 142 1 143 144 1 143 145 1 145 144 1 146 144 1 145 146 1 145 147 1 147 146 1 148 146 1
		 147 148 1 147 149 1 149 148 1 150 148 1 149 150 1 149 151 1 151 150 1 151 152 1 152 150 1
		 153 150 1 152 153 1 152 154 1 154 153 1 154 155 1 155 153 1 154 156 1 156 155 1 156 157 1
		 157 155 1 157 158 1 158 155 1 157 159 1 159 158 1 159 160 1 160 158 1 161 160 1 159 161 1
		 159 162 1 162 161 1 162 163 1 163 161 1 163 164 1 164 161 1 165 164 1 163 165 1 163 166 1
		 166 165 1 166 167 1;
	setAttr ".ed[332:497]" 167 165 1 166 168 1 168 167 1 168 169 1 169 167 1 169 170 1
		 170 167 1 170 171 1 171 167 1 170 172 1 172 171 1 173 171 1 172 173 1 172 174 1 174 173 1
		 175 174 1 172 175 1 172 176 1 176 175 1 176 177 1 177 175 1 176 178 1 178 177 1 178 179 1
		 179 177 1 178 180 1 180 179 1 180 181 1 181 179 1 181 182 1 182 179 1 181 183 1 183 182 1
		 183 184 1 184 182 1 185 182 1 184 185 1 186 185 1 184 186 1 184 187 1 187 186 1 187 188 1
		 188 186 1 189 186 1 188 189 1 190 189 1 188 190 1 188 191 1 191 190 1 192 191 1 188 192 1
		 192 193 1 193 191 1 194 193 1 192 194 1 192 195 1 195 194 1 196 194 1 195 196 1 195 197 1
		 197 196 0 195 198 1 198 197 1 198 199 1 199 197 0 198 200 1 200 199 1 200 201 1 201 199 0
		 200 202 1 202 201 1 200 203 1 203 202 1 203 204 1 204 202 1 205 202 1 204 205 1 204 206 1
		 206 205 0 204 207 1 207 206 0 208 207 1 204 208 1 208 209 1 209 207 0 210 209 0 208 210 1
		 208 211 1 211 210 1 211 212 1 212 210 0 211 213 1 213 212 1 211 214 1 214 213 1 214 215 1
		 215 213 1 216 215 1 214 216 1 214 217 1 217 216 1 218 216 1 217 218 1 217 219 1 219 218 1
		 219 220 1 220 218 1 219 221 1 221 220 1 222 220 1 221 222 1 221 223 1 223 222 1 224 222 1
		 223 224 1 225 224 1 223 225 1 178 225 1 223 178 1 169 224 1 225 169 1 169 226 1 226 224 1
		 226 227 1 227 224 1 226 228 1 228 227 1 228 229 1 229 227 1 229 230 1 230 227 1 230 222 1
		 222 227 1 229 231 1 231 230 1 232 230 1 231 232 0 232 220 1 220 230 1 229 233 1 233 231 0
		 234 233 1 229 234 1 234 235 1 235 233 0 236 235 1 234 236 1 237 236 1 234 237 1 234 228 1
		 228 237 1 228 238 1 238 237 1 239 237 1 238 239 1 238 240 1 240 239 1 241 239 1 240 241 1
		 242 241 1 240 242 1 240 166 1 166 242 1 243 241 1 242 243 1 242 162 1;
	setAttr ".ed[498:663]" 162 243 1 244 243 1 162 244 1 244 245 1 245 243 1 245 246 1
		 246 243 1 245 247 1 247 246 1 245 248 1 248 247 1 248 249 1 249 247 1 249 250 1 250 247 1
		 250 251 1 251 247 1 252 251 1 250 252 1 250 253 1 253 252 1 253 254 1 254 252 1 255 252 1
		 254 255 1 256 255 1 254 256 1 254 257 1 257 256 0 254 258 1 258 257 1 258 259 1 259 257 0
		 258 260 1 260 259 1 258 261 1 261 260 1 262 260 1 261 262 1 263 262 1 261 263 1 261 264 1
		 264 263 1 265 263 1 264 265 1 264 249 1 249 265 1 249 266 1 266 265 1 267 265 1 266 267 1
		 268 267 1 266 268 1 266 269 1 269 268 1 269 270 1 270 268 1 271 268 1 270 271 1 272 271 1
		 270 272 1 270 154 1 154 272 1 273 271 1 272 273 1 272 274 1 274 273 1 275 273 1 274 275 1
		 274 103 1 103 275 1 276 275 1 103 276 1 276 277 1 277 275 1 278 277 1 276 278 1 276 279 1
		 279 278 1 280 278 1 279 280 1 281 280 1 279 281 1 279 100 1 100 281 1 282 281 1 100 282 1
		 282 283 1 283 281 1 283 284 1 284 281 1 283 285 1 285 284 1 285 286 1 286 284 1 287 284 1
		 286 287 1 286 288 1 288 287 1 288 289 1 289 287 1 289 290 1 290 287 1 290 291 1 291 287 1
		 290 292 1 292 291 1 290 293 1 293 292 1 293 294 1 294 292 1 294 278 1 278 292 1 293 295 1
		 295 294 1 296 294 1 295 296 1 295 297 1 297 296 1 297 298 1 298 296 1 297 299 1 299 298 1
		 299 300 1 300 298 1 300 301 1 301 298 1 301 302 1 302 298 1 301 273 1 273 302 1 300 303 1
		 303 301 1 300 304 1 304 303 1 304 267 1 267 303 1 304 305 1 305 267 1 304 306 1 306 305 1
		 306 307 1 307 305 1 307 263 1 263 305 1 306 308 1 308 307 1 309 308 1 306 309 1 306 310 1
		 310 309 1 311 309 1 310 311 1 299 311 1 310 299 1 312 311 1 299 312 1 313 311 1 312 313 1
		 314 313 1 312 314 1 315 314 1 312 315 1 312 297 1 297 315 1 316 314 1;
	setAttr ".ed[664:829]" 315 316 1 315 317 1 317 316 1 318 316 1 317 318 1 317 319 1
		 319 318 1 320 318 1 319 320 1 289 320 1 319 289 1 321 320 1 289 321 1 322 320 1 321 322 1
		 323 322 1 321 323 1 324 323 1 321 324 1 321 288 1 288 324 1 325 324 1 288 325 1 325 326 1
		 326 324 1 326 327 1 327 324 1 326 328 1 328 327 1 328 329 1 329 327 1 329 330 1 330 327 1
		 330 323 1 323 327 1 330 331 1 331 323 1 330 332 1 332 331 1 332 333 1 333 331 1 333 334 1
		 334 331 1 334 322 1 322 331 1 334 335 1 335 322 1 334 336 1 336 335 1 336 337 1 337 335 1
		 337 318 1 318 335 1 336 338 1 338 337 1 339 337 1 338 339 1 338 340 1 340 339 1 340 341 1
		 341 339 1 340 342 1 342 341 1 342 343 1 343 341 1 343 313 1 313 341 1 343 344 1 344 313 1
		 343 345 1 345 344 1 346 344 1 345 346 1 345 347 1 347 346 1 348 346 1 347 348 1 347 349 1
		 349 348 1 350 348 1 349 350 1 351 350 1 349 351 1 349 352 1 352 351 0 349 353 1 353 352 1
		 353 354 1 354 352 0 353 355 1 355 354 1 353 356 1 356 355 1 357 355 1 356 357 1 356 358 1
		 358 357 1 359 357 1 358 359 1 342 359 1 358 342 1 360 359 1 342 360 1 361 359 1 360 361 1
		 362 361 1 360 362 1 363 362 1 360 363 1 360 340 1 340 363 1 364 362 1 363 364 1 363 365 1
		 365 364 1 366 364 1 365 366 1 365 367 1 367 366 1 368 366 1 367 368 1 333 368 1 367 333 1
		 369 368 1 333 369 1 369 370 1 370 368 1 370 371 1 371 368 1 370 372 1 372 371 1 373 372 1
		 370 373 1 374 373 1 370 374 1 375 373 1 374 375 1 374 376 1 376 375 1 377 375 1 376 377 1
		 378 377 1 376 378 1 376 379 1 379 378 1 379 380 1 380 378 1 381 378 1 380 381 1 382 381 1
		 380 382 1 380 383 1 383 382 1 380 384 1 384 383 1 384 385 1 385 383 1 384 329 1 329 385 1
		 384 386 1 386 329 1 384 379 1 379 386 1 379 387 1 387 386 1 387 332 1;
	setAttr ".ed[830:995]" 332 386 1 387 369 1 369 332 1 387 374 1 374 369 1 329 388 1
		 388 385 1 389 385 1 388 389 1 388 390 1 390 389 1 390 391 1 391 389 1 390 392 1 392 391 1
		 390 393 1 393 392 1 393 394 1 394 392 1 393 395 1 395 394 1 395 396 1 396 394 1 397 394 1
		 396 397 1 396 398 1 398 397 1 396 399 1 399 398 1 399 400 1 400 398 1 399 401 1 401 400 1
		 401 402 1 402 400 1 403 400 1 402 403 1 402 404 1 404 403 1 404 405 1 405 403 1 404 406 1
		 406 405 1 404 407 1 407 406 1 407 408 1 408 406 1 407 409 1 409 408 1 409 410 1 410 408 1
		 409 92 1 92 410 1 411 408 1 410 411 1 410 85 1 85 411 1 410 90 1 90 85 1 411 412 1
		 412 408 1 411 413 1 413 412 1 411 84 1 84 413 1 78 413 1 84 78 1 414 412 1 413 414 1
		 76 414 1 413 76 1 415 412 1 414 415 1 416 415 1 414 416 1 74 416 1 414 74 1 417 415 1
		 416 417 1 418 417 1 416 418 1 72 418 1 416 72 1 419 417 1 418 419 1 420 419 1 418 420 1
		 70 420 1 418 70 1 421 419 1 420 421 1 422 421 1 420 422 1 68 422 1 420 68 1 423 421 1
		 422 423 1 424 423 1 422 424 1 66 424 1 422 66 1 425 423 1 424 425 1 426 425 1 424 426 1
		 64 426 1 424 64 1 427 425 1 426 427 1 428 427 1 426 428 1 62 428 1 426 62 1 429 427 1
		 428 429 1 430 429 1 428 430 1 60 430 1 428 60 1 430 431 1 431 429 1 431 432 1 432 429 1
		 432 433 1 433 429 1 434 433 1 432 434 1 432 435 1 435 434 1 435 436 1 436 434 1 436 437 1
		 437 434 1 437 438 1 438 434 1 437 439 1 439 438 1 439 440 1 440 438 1 441 438 1 440 441 1
		 440 442 1 442 441 1 440 443 1 443 442 1 443 444 1 444 442 1 443 445 1 445 444 1 445 446 1
		 446 444 1 445 447 1 447 446 1 447 448 1 448 446 1 403 448 1 447 403 1 419 446 1 448 419 1
		 398 447 1 445 398 1 421 444 1 446 421 1 397 445 1 443 397 1 443 449 1;
	setAttr ".ed[996:1161]" 449 397 1 423 442 1 444 423 1 440 449 1 425 441 1 442 425 1
		 441 433 1 433 438 1 427 433 1 441 427 1 439 449 1 392 449 1 439 392 1 391 439 1 437 391 1
		 437 450 1 450 391 1 436 450 1 436 451 1 451 450 1 451 452 1 452 450 1 452 389 1 389 450 1
		 453 452 1 451 453 1 454 453 1 451 454 1 455 454 1 451 455 1 455 456 1 456 454 1 455 457 1
		 457 456 1 455 435 1 435 457 1 458 457 1 435 458 1 458 459 1 459 457 1 458 460 1 460 459 1
		 458 431 1 431 460 1 461 460 1 431 461 1 461 54 1 54 460 1 54 462 1 462 460 1 462 459 1
		 463 459 1 462 463 1 464 463 1 462 464 1 52 464 1 462 52 1 465 463 1 464 465 1 466 465 1
		 464 466 1 51 466 1 464 51 1 51 467 1 467 466 1 467 468 1 468 466 1 468 469 1 469 466 1
		 470 469 1 468 470 1 471 470 1 468 471 1 468 472 1 472 471 1 468 473 1 473 472 1 473 42 1
		 42 472 1 474 471 1 472 474 1 472 40 1 40 474 1 475 471 1 474 475 1 476 475 1 474 476 1
		 474 38 1 38 476 1 477 475 1 476 477 1 478 477 1 476 478 1 476 36 1 36 478 1 479 477 1
		 478 479 1 480 479 1 478 480 1 478 34 1 34 480 1 481 479 1 480 481 1 482 481 1 480 482 1
		 480 32 1 32 482 1 483 481 1 482 483 1 484 483 1 482 484 1 482 30 1 30 484 1 485 483 1
		 484 485 1 486 485 1 484 486 1 484 28 1 28 486 1 487 485 1 486 487 1 488 487 1 486 488 1
		 486 26 1 26 488 1 489 487 1 488 489 1 19 489 1 488 19 1 488 24 1 24 19 1 489 490 1
		 490 487 1 491 487 1 490 491 1 490 492 1 492 491 1 492 493 1 493 491 1 493 494 1 494 491 1
		 493 495 1 495 494 1 495 496 1 496 494 1 495 497 1 497 496 1 497 498 1 498 496 1 497 499 1
		 499 498 1 499 500 1 500 498 1 499 501 1 501 500 1 501 502 1 502 500 1 501 503 1 503 502 1
		 503 470 1 470 502 1 470 475 1 475 502 1 501 504 1 504 503 1 504 505 1;
	setAttr ".ed[1162:1327]" 505 503 1 504 506 1 506 505 1 506 507 1 507 505 1 506 508 1
		 508 507 1 508 509 1 509 507 1 508 456 1 456 509 1 510 456 1 508 510 1 508 511 1 511 510 1
		 511 512 1 512 510 1 512 454 1 454 510 1 511 513 1 513 512 1 513 382 1 382 512 1 514 382 1
		 513 514 1 515 514 1 513 515 1 513 516 1 516 515 1 517 515 1 516 517 1 516 518 1 518 517 1
		 516 504 1 504 518 1 516 511 1 511 504 1 519 517 1 518 519 1 518 499 1 499 519 1 520 517 1
		 519 520 1 521 520 1 519 521 1 519 497 1 497 521 1 522 520 1 521 522 1 523 522 1 521 523 1
		 521 495 1 495 523 1 524 522 1 523 524 1 525 524 1 523 525 1 523 493 1 493 525 1 525 526 1
		 526 524 1 527 526 1 525 527 1 492 527 1 525 492 1 528 527 1 492 528 1 528 529 1 529 527 1
		 530 529 1 528 530 1 531 530 1 528 531 1 528 490 1 490 531 1 15 530 1 531 15 1 530 532 1
		 532 529 1 532 533 1 533 529 1 534 529 1 533 534 1 533 535 1 535 534 1 535 536 1 536 534 1
		 536 526 1 526 534 1 537 526 1 536 537 1 536 538 1 538 537 1 538 539 1 539 537 1 539 540 1
		 540 537 1 524 537 1 540 524 1 541 540 1 539 541 1 539 542 1 542 541 1 543 541 1 542 543 1
		 542 544 1 544 543 1 544 545 1 545 543 1 544 546 1 546 545 1 547 545 1 546 547 1 546 548 1
		 548 547 1 549 547 1 548 549 1 548 550 1 550 549 1 550 551 1 551 549 1 550 552 1 552 551 1
		 553 551 1 552 553 1 552 554 1 554 553 1 554 555 1 555 553 1 554 556 1 556 555 1 557 555 1
		 556 557 1 556 558 1 558 557 1 558 559 1 559 557 1 558 560 1 560 559 1 561 559 1 560 561 1
		 562 561 1 560 562 1 560 563 1 563 562 0 560 564 1 564 563 1 564 565 1 565 563 0 564 566 1
		 566 565 1 564 567 1 567 566 1 568 566 1 567 568 1 569 568 1 567 569 1 567 556 1 556 569 1
		 570 568 1 569 570 1 569 571 1 571 570 1 572 570 1 571 572 1 573 572 1;
	setAttr ".ed[1328:1493]" 571 573 1 571 552 1 552 573 1 574 572 1 573 574 1 573 575 1
		 575 574 1 576 574 1 575 576 1 577 576 1 575 577 1 575 548 1 548 577 1 578 576 1 577 578 1
		 579 578 1 577 579 1 577 546 1 546 579 1 580 578 1 579 580 1 579 581 1 581 580 1 582 580 1
		 581 582 1 583 582 1 581 583 1 581 542 1 542 583 1 584 582 1 583 584 1 538 584 1 583 538 1
		 585 584 1 538 585 1 585 586 1 586 584 1 587 586 1 585 587 1 535 587 1 585 535 1 588 587 1
		 535 588 1 588 589 1 589 587 1 590 589 1 588 590 1 591 590 1 588 591 1 588 533 1 533 591 1
		 592 590 1 591 592 1 591 593 1 593 592 1 594 592 1 593 594 1 13 594 1 593 13 1 595 594 1
		 13 595 1 595 596 1 596 594 1 1 596 1 595 1 1 1 597 1 597 596 1 597 598 1 598 596 1
		 598 599 1 599 596 1 598 600 1 600 599 1 601 599 1 600 601 1 600 602 1 602 601 1 603 601 1
		 602 603 1 602 604 1 604 603 1 604 605 1 605 603 1 605 589 1 589 603 1 606 589 1 605 606 1
		 605 607 1 607 606 1 607 608 1 608 606 1 608 586 1 586 606 1 609 586 1 608 609 1 608 610 1
		 610 609 1 611 609 1 610 611 1 610 612 1 612 611 1 612 613 1 613 611 1 612 614 1 614 613 1
		 615 613 1 614 615 1 614 616 1 616 615 1 617 615 1 616 617 1 616 618 1 618 617 1 618 619 1
		 619 617 1 618 620 1 620 619 1 621 619 1 620 621 1 620 622 1 622 621 1 622 623 1 623 621 1
		 622 624 1 624 623 1 625 623 1 624 625 1 626 625 1 624 626 1 624 627 1 627 626 0 624 628 1
		 628 627 1 628 629 1 629 627 0 628 630 1 630 629 1 628 631 1 631 630 1 631 632 1 632 630 1
		 633 630 1 632 633 1 632 634 1 634 633 0 632 635 1 635 634 1 636 635 1 632 636 1 636 637 1
		 637 635 1 637 638 1 638 635 1 639 635 1 638 639 1 638 640 1 640 639 0 638 641 1 641 640 0
		 638 642 1 642 641 0 638 643 1 643 642 1 643 644 1 644 642 1 645 642 1;
	setAttr ".ed[1494:1659]" 644 645 1 644 646 1 646 645 1 647 645 1 646 647 1 648 647 1
		 646 648 1 646 649 1 649 648 1 649 650 1 650 648 1 651 648 1 650 651 1 652 651 1 650 652 1
		 650 653 1 653 652 1 653 654 1 654 652 1 655 652 1 654 655 1 654 656 1 656 655 1 657 655 1
		 656 657 1 658 657 1 656 658 1 656 659 1 659 658 1 604 658 1 659 604 1 660 658 1 604 660 1
		 660 661 1 661 658 1 662 661 1 660 662 1 663 662 1 660 663 1 660 602 1 602 663 1 664 662 1
		 663 664 1 663 665 1 665 664 1 666 664 1 665 666 1 665 667 1 667 666 1 668 666 1 667 668 1
		 667 597 1 597 668 1 669 668 1 597 669 1 670 668 1 669 670 1 669 671 1 671 670 0 669 672 1
		 672 671 1 669 1 1 1 672 1 673 671 1 672 673 1 672 674 1 674 673 0 672 0 1 0 674 1
		 673 675 0 675 671 0 670 676 0 676 668 1 677 668 1 676 677 0 677 678 1 678 668 1 679 678 1
		 677 679 1 680 679 1 677 680 0 680 681 1 681 679 1 682 679 1 681 682 1 681 683 1 683 682 1
		 683 684 1 684 682 1 684 685 1 685 682 1 686 682 1 685 686 1 685 664 1 664 686 1 687 685 1
		 684 687 1 684 688 1 688 687 1 688 689 1 689 687 1 689 661 1 661 687 1 657 661 1 689 657 1
		 689 690 1 690 657 1 689 691 1 691 690 1 691 692 1 692 690 1 692 693 1 693 690 1 693 655 1
		 655 690 1 692 694 1 694 693 1 694 651 1 651 693 1 694 695 1 695 651 1 694 696 1 696 695 1
		 697 696 1 694 697 1 697 698 1 698 696 1 699 698 1 697 699 1 700 699 1 697 700 1 697 692 1
		 692 700 1 701 699 1 700 701 1 700 702 1 702 701 1 703 701 1 702 703 1 704 703 1 702 704 1
		 702 688 1 688 704 1 702 691 1 691 688 1 705 703 1 704 705 1 704 683 1 683 705 1 706 705 1
		 683 706 1 706 707 1 707 705 1 707 708 1 708 705 1 707 709 1 709 708 1 709 710 1 710 708 1
		 710 711 1 711 708 1 710 712 1 712 711 1 713 711 1 712 713 1 712 714 1;
	setAttr ".ed[1660:1825]" 714 713 1 715 713 1 714 715 1 714 716 1 716 715 1 716 717 1
		 717 715 1 716 718 1 718 717 1 719 717 1 718 719 1 718 720 1 720 719 1 720 721 1 721 719 1
		 721 722 1 722 719 1 721 723 1 723 722 1 696 722 1 723 696 1 724 723 1 721 724 1 725 724 1
		 721 725 1 725 726 0 726 724 1 726 645 1 645 724 1 726 727 0 727 645 1 724 647 1 647 723 1
		 695 723 1 647 695 1 720 725 0 718 728 1 728 720 0 729 728 1 718 729 1 729 730 1 730 728 0
		 731 730 1 729 731 1 729 732 1 732 731 1 733 731 1 732 733 1 734 733 1 732 734 1 732 714 1
		 714 734 1 735 733 1 734 735 1 734 736 1 736 735 1 736 737 1 737 735 1 738 735 1 737 738 1
		 739 738 1 737 739 1 740 739 0 737 740 1 737 741 1 741 740 1 742 740 0 741 742 1 741 743 1
		 743 742 0 741 744 1 744 743 1 736 744 1 741 736 1 736 710 1 710 744 1 744 745 1 745 743 0
		 744 709 1 709 745 1 709 746 1 746 745 0 739 747 0 747 738 1 747 748 1 748 738 1 748 749 1
		 749 738 1 748 750 1 750 749 1 751 749 1 750 751 1 750 752 1 752 751 1 753 751 1 752 753 0
		 753 731 1 731 751 1 750 754 1 754 752 0 751 733 1 733 749 1 748 754 1 748 755 1 755 754 0
		 747 755 1 747 756 0 756 755 0 749 735 1 734 712 1 712 736 1 729 716 1 716 732 1 753 730 0
		 722 717 1 698 717 1 722 698 1 698 715 1 715 699 1 699 713 1 713 701 1 701 711 1 711 703 1
		 703 708 1 707 746 1 706 746 1 706 681 1 681 746 1 700 691 1 684 704 1 687 662 1 662 685 1
		 686 679 1 680 746 0 686 678 1 686 666 1 666 678 1 665 598 1 598 667 1 663 600 1 600 665 1
		 757 659 1 656 757 1 757 607 1 607 659 1 757 758 1 758 607 1 757 759 1 759 758 1 759 760 1
		 760 758 1 759 761 1 761 760 1 762 760 1 761 762 1 761 763 1 763 762 1 763 764 1 764 762 1
		 763 765 1 765 764 1 766 764 1 765 766 1 765 767 1 767 766 1 768 766 1;
	setAttr ".ed[1826:1991]" 767 768 1 767 636 1 636 768 1 636 631 1 631 768 1 631 620 1
		 620 768 1 768 618 1 618 766 1 765 769 1 769 767 1 770 769 1 765 770 1 770 771 1 771 769 1
		 771 643 1 643 769 1 643 637 1 637 769 1 649 771 1 770 649 1 770 772 1 772 649 1 770 763 1
		 763 772 1 637 767 1 766 616 1 616 764 1 764 614 1 614 762 1 761 772 1 653 772 1 761 653 1
		 762 612 1 612 760 1 759 653 1 760 610 1 610 758 1 757 654 1 654 759 1 693 652 1 650 772 1
		 695 648 1 646 771 1 644 771 1 727 642 0 639 634 0 628 622 1 622 631 1 633 629 0 626 773 0
		 773 625 1 773 565 0 565 625 1 625 568 1 568 623 1 623 570 1 570 621 1 621 572 1 572 619 1
		 619 574 1 574 617 1 617 576 1 576 615 1 615 578 1 578 613 1 613 580 1 580 611 1 611 582 1
		 582 609 1 608 758 1 605 659 1 603 590 1 590 601 1 601 592 1 592 599 1 599 594 1 591 532 1
		 532 593 1 532 14 1 14 593 1 606 587 1 609 584 1 579 544 1 544 581 1 573 550 1 550 575 1
		 569 554 1 554 571 1 625 566 1 564 558 1 558 567 1 562 774 0 774 561 1 774 775 1 775 561 1
		 775 776 1 776 561 1 775 777 1 777 776 1 778 776 1 777 778 1 777 779 1 779 778 1 779 780 1
		 780 778 1 781 778 1 780 781 1 371 781 1 780 371 1 780 366 1 366 371 1 781 782 1 782 778 1
		 783 782 1 781 783 1 372 783 1 781 372 1 784 783 1 372 784 1 784 555 1 555 783 1 783 557 1
		 557 782 1 779 364 1 364 780 1 777 785 1 785 779 1 777 786 1 786 785 1 786 787 1 787 785 1
		 787 361 1 361 785 1 787 788 1 788 361 1 789 788 1 787 789 1 789 790 1 790 788 1 791 790 1
		 789 791 0 791 792 0 792 790 1 792 793 1 793 790 1 792 794 0 794 793 1 794 795 0 795 793 1
		 795 355 1 355 793 1 793 788 1 793 357 1 357 788 1 786 789 1 786 796 1 796 789 0 775 796 1
		 786 775 1 775 797 1 797 796 0 785 362 1 362 779 1 782 776 1 782 559 1;
	setAttr ".ed[1992:2157]" 559 776 1 774 797 0 784 553 1 784 798 1 798 553 1 784 373 1
		 373 798 1 798 551 1 799 551 1 798 799 1 798 375 1 375 799 1 799 549 1 799 800 1 800 549 1
		 799 377 1 377 800 1 801 800 1 377 801 1 802 800 1 801 802 1 801 803 1 803 802 1 804 802 1
		 803 804 1 803 805 1 805 804 1 806 804 1 805 806 1 805 807 1 807 806 1 805 515 1 515 807 1
		 808 806 1 807 808 1 807 520 1 520 808 1 541 806 1 808 541 1 806 543 1 543 804 1 803 514 1
		 514 805 1 381 514 1 803 381 1 804 545 1 545 802 1 801 381 1 802 547 1 547 800 1 539 583 1
		 808 540 1 808 522 1 522 540 1 536 585 1 530 14 1 534 527 1 807 517 1 463 507 1 509 463 1
		 506 511 1 465 505 1 507 465 1 465 469 1 469 505 1 469 503 1 501 518 1 502 477 1 477 500 1
		 500 479 1 479 498 1 498 481 1 481 496 1 496 483 1 483 494 1 494 485 1 485 491 1 489 531 1
		 17 531 1 489 17 1 467 473 1 467 44 1 44 473 1 509 459 1 509 457 1 512 453 1 512 383 1
		 383 453 1 453 385 1 385 452 1 436 455 1 432 458 1 430 461 1 58 461 1 430 58 1 448 417 1
		 448 405 1 405 417 1 405 415 1 406 412 1 415 406 1 809 409 1 407 809 1 407 810 1 810 809 1
		 811 809 1 810 811 1 810 812 1 812 811 1 282 811 1 812 282 1 282 98 1 98 811 1 810 402 1
		 402 812 1 811 96 1 96 809 1 809 94 1 94 409 1 404 810 1 447 400 1 401 812 1 283 812 1
		 401 283 1 285 401 1 399 285 1 399 813 1 813 285 1 396 813 1 449 394 1 395 813 1 325 813 1
		 395 325 1 325 286 1 286 813 1 326 395 1 393 326 1 328 393 1 390 328 1 388 328 1 801 378 1
		 376 387 1 365 336 1 336 367 1 363 338 1 338 365 1 788 359 1 356 345 1 345 358 1 353 347 1
		 347 356 1 795 354 0 351 814 0 814 350 1 814 815 1 815 350 1 815 816 1 816 350 1 815 262 1
		 262 816 1 307 816 1 262 307 1 814 817 0 817 815 1 817 260 1 260 815 1;
	setAttr ".ed[2158:2323]" 816 348 1 816 308 1 308 348 1 308 346 1 346 309 1 309 344 1
		 343 358 1 341 314 1 314 339 1 339 316 1 316 337 1 334 367 1 330 386 1 335 320 1 317 293 1
		 293 319 1 315 295 1 295 317 1 344 311 1 304 310 1 300 310 1 303 271 1 271 301 1 302 296 1
		 302 277 1 277 296 1 277 294 1 290 319 1 292 280 1 280 291 1 280 284 1 284 291 1 276 101 1
		 101 279 1 302 275 1 274 151 1 151 103 1 272 152 1 152 274 1 303 268 1 269 156 1 156 270 1
		 269 818 1 818 156 1 269 248 1 248 818 1 266 248 1 305 265 1 261 253 1 253 264 1 258 253 1
		 817 259 0 256 819 0 819 255 1 819 820 1 820 255 1 820 821 1 821 255 1 820 822 1 822 821 1
		 823 821 1 822 823 1 822 239 1 239 823 1 823 251 1 251 821 1 823 246 1 246 251 1 823 241 1
		 241 246 1 236 822 1 820 236 1 824 236 1 820 824 1 819 824 0 821 252 1 250 264 1 245 818 1
		 244 818 1 244 157 1 157 818 1 238 168 1 168 240 1 238 226 1 226 168 1 822 237 1 824 235 0
		 221 180 1 180 223 1 219 180 1 219 825 1 825 180 1 232 218 1 232 826 0 826 218 1 217 825 1
		 827 825 1 217 827 1 217 828 1 828 827 1 828 829 1 829 827 1 181 827 1 829 181 1 828 203 1
		 203 829 1 828 208 1 208 203 1 181 825 1 826 216 1 826 830 0 830 216 1 214 828 1 830 215 1
		 830 831 0 831 215 1 831 832 1 832 215 1 831 833 0 833 832 1 834 832 1 833 834 0 835 832 1
		 834 835 0 835 213 1 213 832 1 211 828 1 835 212 0 200 829 1 183 829 1 200 183 1 205 201 0
		 198 183 1 195 184 1 184 198 1 196 836 0 836 194 1 836 837 1 837 194 1 836 838 0 838 837 1
		 838 839 1 839 837 1 839 840 1 840 837 1 840 193 1 193 837 1 841 193 1 840 841 1 840 842 1
		 842 841 1 840 843 1 843 842 1 843 844 1 844 842 1 845 844 1 843 845 1 839 845 1 843 839 1
		 846 845 1 839 846 1 839 847 1 847 846 0 846 848 1 848 845 1 846 849 0;
	setAttr ".ed[2324:2489]" 849 848 1 849 850 0 850 848 1 850 851 1 851 848 1 852 848 1
		 851 852 1 853 852 1 851 853 1 854 853 1 851 854 1 855 853 1 854 855 0 855 856 1 856 853 1
		 857 856 1 855 857 0 857 858 1 858 856 1 858 859 1 859 856 1 860 856 1 859 860 1 861 860 1
		 859 861 1 862 861 1 859 862 1 863 862 1 859 863 1 863 864 1 864 862 1 864 865 1 865 862 1
		 866 862 1 865 866 1 865 867 1 867 866 1 868 866 1 867 868 1 867 869 1 869 868 1 870 868 1
		 869 870 1 869 871 1 871 870 1 872 870 1 871 872 1 871 873 1 873 872 1 874 872 1 873 874 1
		 873 875 1 875 874 1 875 876 1 876 874 1 877 874 1 876 877 1 876 878 1 878 877 1 878 879 1
		 879 877 1 879 880 1 880 877 1 881 880 1 879 881 1 879 174 1 174 881 1 174 882 1 882 881 1
		 882 189 1 189 881 1 189 883 1 883 881 1 883 880 1 884 880 1 883 884 1 883 885 1 885 884 1
		 190 885 1 883 190 1 190 886 1 886 885 1 887 885 1 886 887 1 841 887 1 886 841 1 887 888 1
		 888 885 1 889 888 1 887 889 1 887 842 1 842 889 1 842 890 1 890 889 1 891 889 1 890 891 1
		 890 852 1 852 891 1 860 891 1 852 860 1 890 844 1 844 852 1 891 892 1 892 889 1 891 861 1
		 861 892 1 866 892 1 861 866 1 893 889 1 892 893 1 868 893 1 892 868 1 893 888 1 894 888 1
		 893 894 1 870 894 1 893 870 1 884 888 1 894 884 1 895 884 1 894 895 1 872 895 1 894 872 1
		 190 841 1 895 880 1 895 877 1 878 173 1 173 879 1 878 896 1 896 173 1 897 896 1 878 897 1
		 897 164 1 164 896 1 898 164 1 897 898 1 897 899 1 899 898 1 900 898 1 899 900 1 875 900 1
		 899 875 1 875 901 1 901 900 1 902 900 1 901 902 1 903 902 1 901 903 1 901 904 1 904 903 1
		 905 903 1 904 905 1 904 906 1 906 905 1 907 905 1 906 907 1 906 908 1 908 907 1 909 907 1
		 908 909 1 908 910 1 910 909 1 911 909 1 910 911 1 910 912 1 912 911 1;
	setAttr ".ed[2490:2655]" 913 911 1 912 913 1 912 914 1 914 913 1 915 913 1 914 915 1
		 914 916 1 916 915 1 917 915 1 916 917 1 916 918 1 918 917 1 919 917 1 918 919 1 918 920 1
		 920 919 1 920 921 1 921 919 1 921 922 1 922 919 1 922 923 1 923 919 1 922 131 1 131 923 1
		 924 131 1 922 924 1 922 925 1 925 924 1 926 924 1 925 926 1 925 927 1 927 926 0 925 928 1
		 928 927 1 925 929 1 929 928 1 925 921 1 921 929 1 921 930 1 930 929 1 931 929 1 930 931 1
		 930 932 1 932 931 1 933 931 1 932 933 1 932 934 1 934 933 1 934 935 1 935 933 1 935 936 1
		 936 933 1 936 937 1 937 933 1 936 938 1 938 937 1 939 937 1 938 939 1 938 940 1 940 939 1
		 940 928 1 928 939 1 941 928 1 940 941 1 940 942 1 942 941 0 943 942 1 940 943 1 943 944 1
		 944 942 0 943 945 1 945 944 0 943 946 1 946 945 1 943 947 1 947 946 1 947 948 1 948 946 1
		 949 946 1 948 949 1 948 950 1 950 949 0 948 951 1 951 950 1 952 951 1 948 952 1 952 953 1
		 953 951 1 953 954 1 954 951 1 955 951 1 954 955 1 954 956 1 956 955 0 954 957 1 957 956 1
		 954 958 1 958 957 1 958 959 1 959 957 1 960 957 1 959 960 1 959 961 1 961 960 1 962 960 1
		 961 962 1 963 962 1 961 963 1 961 964 1 964 963 1 965 963 1 964 965 1 964 966 1 966 965 1
		 966 967 1 967 965 1 967 968 1 968 965 1 968 969 1 969 965 1 968 970 1 970 969 1 970 971 1
		 971 969 1 972 971 1 970 972 1 973 972 1 970 973 1 970 974 1 974 973 0 973 975 0 975 972 1
		 975 976 1 976 972 1 976 977 1 977 972 1 978 977 1 976 978 1 979 978 1 976 979 1 980 979 1
		 976 980 1 980 981 0 981 979 1 981 982 1 982 979 1 982 983 1 983 979 1 984 983 1 982 984 1
		 985 984 1 982 985 1 986 985 1 982 986 1 986 987 0 987 985 1 987 988 1 988 985 1 988 989 1
		 989 985 1 990 989 1 988 990 1 988 991 1 991 990 1 991 992 1 992 990 1;
	setAttr ".ed[2656:2821]" 993 990 1 992 993 1 992 994 1 994 993 1 995 993 1 994 995 1
		 996 995 1 994 996 1 997 996 1 994 997 1 994 998 1 998 997 1 998 999 1 999 997 1 1000 997 1
		 999 1000 1 1001 1000 1 999 1001 1 999 1002 1 1002 1001 0 999 1003 1 1003 1002 1 1003 1004 1
		 1004 1002 0 1003 1005 1 1005 1004 1 998 1005 1 1003 998 1 998 992 1 992 1005 1 1005 1006 1
		 1006 1004 0 1005 991 1 991 1006 1 1007 1006 0 991 1007 1 991 1008 1 1008 1007 0 1001 1009 0
		 1009 1000 1 1009 1010 1 1010 1000 1 1010 1011 1 1011 1000 1 1010 1012 1 1012 1011 1
		 1013 1011 1 1012 1013 1 1012 1014 1 1014 1013 1 1014 1015 1 1015 1013 1 1014 1016 1
		 1016 1015 1 1014 1017 1 1017 1016 1 1017 1018 1 1018 1016 1 1017 1019 1 1019 1018 1
		 1019 1020 1 1020 1018 1 1019 1021 1 1021 1020 1 1021 1022 1 1022 1020 1 1021 1023 1
		 1023 1022 1 1024 1022 1 1023 1024 1 1023 1025 1 1025 1024 1 1025 1026 0 1026 1024 1
		 1026 1027 1 1027 1024 1 1028 1024 1 1027 1028 1 1029 1028 1 1027 1029 1 1030 1029 0
		 1027 1030 1 1027 1031 1 1031 1030 1 1031 1032 0 1032 1030 0 1029 1033 0 1033 1028 1
		 1033 1034 1 1034 1028 1 1034 1022 1 1022 1028 1 1033 1035 1 1035 1034 1 1035 1020 1
		 1020 1034 1 1033 1036 0 1036 1035 1 1037 1035 1 1036 1037 0 1038 1035 1 1037 1038 1
		 1039 1038 1 1037 1039 0 1040 1038 1 1039 1040 1 1041 1040 1 1039 1041 0 1042 1040 1
		 1041 1042 1 1043 1042 1 1041 1043 0 1044 1042 1 1043 1044 1 1045 1044 1 1043 1045 0
		 1045 1046 1 1046 1044 1 1046 995 1 995 1044 1 1047 1044 1 995 1047 1 1046 1048 1
		 1048 995 1 1049 1048 1 1046 1049 1 1046 1050 1 1050 1049 1 1050 1051 1 1051 1049 1
		 1052 1049 1 1051 1052 1 1051 1053 1 1053 1052 1 1054 1052 1 1053 1054 1 1053 1055 1
		 1055 1054 1 983 1054 1 1055 983 1 1055 978 1 978 983 1 1055 1056 1 1056 978 1 1057 1056 1
		 1055 1057 1 1057 1058 1 1058 1056 1 1059 1058 1 1057 1059 1 1057 1060 1 1060 1059 1
		 1061 1059 1 1060 1061 1 1060 1062 1 1062 1061 0 1060 1051 1 1051 1062 1 1061 1063 0
		 1063 1059 1 1063 1064 1 1064 1059 1 1063 1065 0 1065 1064 1 1065 1066 1 1066 1064 1;
	setAttr ".ed[2822:2987]" 1067 1064 1 1066 1067 1 1066 962 1 962 1067 1 1068 1067 1
		 962 1068 1 1068 1069 1 1069 1067 1 1069 1058 1 1058 1067 1 971 1069 1 1068 971 1
		 971 977 1 977 1069 1 977 1056 1 1056 1069 1 1066 1070 1 1070 962 1 1071 1070 1 1066 1071 1
		 1072 1071 0 1066 1072 1 1071 1073 0 1073 1070 1 1073 960 1 960 1070 1 1058 1064 1
		 1065 1072 0 1057 1053 1 1053 1060 1 1054 1074 1 1074 1052 1 1074 1075 1 1075 1052 1
		 1074 1076 1 1076 1075 1 1076 1048 1 1048 1075 1 1076 993 1 993 1048 1 989 1076 1
		 1074 989 1 1074 984 1 984 989 1 1054 984 1 1075 1049 1 1050 1062 0 1045 1050 0 1047 1042 1
		 1015 1042 1 1047 1015 1 1015 1040 1 1040 1016 1 1016 1038 1 1038 1018 1 1018 1035 1
		 1026 1031 0 1077 1025 0 1023 1077 1 1078 1077 1 1023 1078 1 1078 1079 1 1079 1077 0
		 1078 1080 1 1080 1079 1 1078 1081 1 1081 1080 1 1082 1080 1 1081 1082 1 1083 1082 1
		 1081 1083 1 1081 1084 1 1084 1083 1 1085 1083 1 1084 1085 1 1017 1085 1 1084 1017 1
		 1085 1086 1 1086 1083 1 1012 1086 1 1085 1012 1 1086 1087 1 1087 1083 1 1086 1088 1
		 1088 1087 0 1010 1088 1 1086 1010 1 1081 1089 1 1089 1084 1 1089 1019 1 1019 1084 1
		 1087 1082 0 1082 1090 0 1090 1080 1 1090 1091 0 1091 1080 1 1078 1089 1 1078 1021 1
		 1021 1089 1 1091 1079 0 1014 1085 1 1047 1013 1 1047 996 1 996 1013 1 996 1011 1
		 1009 1088 0 1011 997 1 1076 990 1 988 1008 1 987 1008 0 981 986 0 975 980 0 1068 969 1
		 1068 963 1 963 969 1 968 974 1 968 1092 1 1092 974 0 967 1092 1 967 1093 1 1093 1092 0
		 967 1094 1 1094 1093 1 1094 1095 1 1095 1093 0 1094 1096 1 1096 1095 1 1094 1097 1
		 1097 1096 1 1097 1098 1 1098 1096 1 1098 1099 1 1099 1096 1 1098 935 1 935 1099 1
		 1100 935 1 1098 1100 1 1098 1101 1 1101 1100 1 953 1100 1 1101 953 1 1101 958 1 958 953 1
		 1101 1102 1 1102 958 1 1097 1102 1 1101 1097 1 1097 966 1 966 1102 1 1103 1096 1
		 1099 1103 1 1099 1104 1 1104 1103 0 1099 934 1 934 1104 1 1105 1104 1 934 1105 1
		 1105 1106 1 1106 1104 0 1105 1107 1 1107 1106 1 1107 1108 1 1108 1106 0 858 1108 1
		 1107 858 1 1107 863 1;
	setAttr ".ed[2988:3153]" 863 858 1 1107 1109 1 1109 863 1 1107 1110 1 1110 1109 1
		 918 1109 1 1110 918 1 918 1111 1 1111 1109 1 864 1109 1 1111 864 1 1112 864 1 1111 1112 1
		 1111 916 1 916 1112 1 1107 1113 1 1113 1110 1 1113 920 1 920 1110 1 1113 930 1 930 920 1
		 1105 1113 1 1105 932 1 932 1113 1 1094 966 1 1103 1095 0 964 1102 1 959 1102 1 964 959 1
		 1073 957 1 1073 956 0 952 1100 1 952 936 1 936 1100 1 952 947 1 947 936 1 955 950 0
		 943 938 1 938 947 1 949 945 0 939 931 1 931 937 1 939 929 1 941 927 0 926 129 1 129 924 1
		 923 917 1 1114 917 1 923 1114 1 923 132 1 132 1114 1 1114 915 1 1115 915 1 1114 1115 1
		 1114 134 1 134 1115 1 914 1112 1 1116 1112 1 914 1116 1 1116 865 1 865 1112 1 1115 913 1
		 1115 1117 1 1117 913 1 1115 136 1 136 1117 1 912 1116 1 1118 1116 1 912 1118 1 1118 867 1
		 867 1116 1 1117 911 1 1117 1119 1 1119 911 1 1117 138 1 138 1119 1 910 1118 1 1120 1118 1
		 910 1120 1 1120 869 1 869 1118 1 1119 909 1 1119 1121 1 1121 909 1 1119 140 1 140 1121 1
		 908 1120 1 1122 1120 1 908 1122 1 1122 871 1 871 1120 1 1121 907 1 1121 1123 1 1123 907 1
		 1121 142 1 142 1123 1 906 1122 1 1124 1122 1 906 1124 1 1124 873 1 873 1122 1 1123 905 1
		 1123 1125 1 1125 905 1 1123 144 1 144 1125 1 904 1124 1 904 875 1 875 1124 1 1125 903 1
		 1125 1126 1 1126 903 1 1125 146 1 146 1126 1 1126 902 1 1126 1127 1 1127 902 1 1126 1128 1
		 1128 1127 1 1128 1129 1 1129 1127 1 1129 1130 1 1130 1127 1 1129 158 1 158 1130 1
		 153 1129 1 1128 153 1 1126 148 1 148 1128 1 1130 902 1 1130 900 1 1130 160 1 160 900 1
		 160 898 1 897 876 1 876 899 1 895 874 1 857 1108 0 860 853 1 844 848 1 850 854 0
		 838 847 0 192 187 1 187 195 1 841 191 1 882 186 1 882 185 1 175 185 1 882 175 1 185 177 1
		 177 182 1 176 225 1 170 225 1 176 170 1 896 171 1 165 171 1 896 165 1 163 242 1 898 161 1
		 159 244 1 1129 155 1 1128 150 1 149 104 1 104 151 1 147 106 1 106 149 1;
	setAttr ".ed[3154:3319]" 145 108 1 108 147 1 143 110 1 110 145 1 141 112 1 112 143 1
		 139 114 1 114 141 1 137 116 1 116 139 1 135 118 1 118 137 1 133 120 1 120 135 1 130 122 1
		 122 133 1 127 122 1 926 128 0 125 1131 0 1131 124 1 1131 1132 1 1132 124 1 1132 1133 1
		 1133 124 1 1132 1134 1 1134 1133 1 1135 1134 1 1132 1135 1 1136 1135 1 1132 1136 1
		 1136 1137 0 1137 1135 1 1137 1138 1 1138 1135 1 1138 1139 1 1139 1135 1 82 1139 1
		 1138 82 1 87 1139 1 82 87 1 87 1140 1 1140 1139 1 1140 1134 1 1134 1139 1 1140 1141 1
		 1141 1134 1 1140 1142 1 1142 1141 1 1142 117 1 117 1141 1 88 1142 1 1140 88 1 1143 1142 1
		 88 1143 1 1143 115 1 115 1142 1 1137 1144 0 1144 1138 1 1144 81 1 81 1138 1 1144 1145 0
		 1145 81 1 1141 1133 1 1141 119 1 119 1133 1 1131 1136 0 1133 121 1 1143 113 1 1143 1146 1
		 1146 113 1 1143 89 1 89 1146 1 1146 111 1 1146 1147 1 1147 111 1 1146 91 1 91 1147 1
		 1147 109 1 1147 1148 1 1148 109 1 1147 93 1 93 1148 1 1148 107 1 1148 1149 1 1149 107 1
		 1148 95 1 95 1149 1 1149 105 1 1149 1150 1 1150 105 1 1149 97 1 97 1150 1 1150 102 1
		 1150 99 1 1145 79 1 1145 1151 0 1151 79 1 1151 77 1 1151 1152 0 1152 77 1 1152 75 1
		 1152 1153 0 1153 75 1 1153 73 1 1153 1154 0 1154 73 1 1154 71 1 1154 1155 0 1155 71 1
		 1155 69 1 1155 1156 0 1156 69 1 1156 67 1 1156 1157 0 1157 67 1 1157 65 1 1157 1158 0
		 1158 65 1 1158 63 1 1158 1159 0 1159 63 1 1159 61 1 1159 1160 0 1160 61 1 1160 59 1
		 1160 1161 0 1161 59 1 1161 57 1 1161 1162 0 1162 57 1 55 461 1 1162 56 1 1162 1163 0
		 1163 56 1 1164 56 1 1163 1164 0 1165 56 1 1164 1165 1 1166 1165 1 1164 1166 0 1166 1167 0
		 1167 1165 1 1167 53 1 53 1165 1 1167 50 1 48 467 1 1167 49 0 46 467 1 1168 21 1 22 1168 0
		 1169 21 1 1168 1169 1 1170 1169 1 1168 1170 0 1170 7 1 7 1169 1 1171 7 1 1170 1171 1
		 1172 1171 0 1170 1172 0 1169 1173 1 1173 21 1 1169 8 1 8 1173 1 1173 18 1 1173 16 1;
	setAttr ".ed[3320:3328]" 1173 10 1 10 16 1 11 595 1 2 595 1 11 2 1 9 2 1 1171 5 0
		 3 9 1 4 674 0;
	setAttr -s 1174 ".n";
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
	setAttr ".n[332:497]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[498:663]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[664:829]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[830:995]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[996:1161]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1162:1173]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
		 1e+20;
	setAttr -s 2156 -ch 6468 ".fc";
	setAttr ".fc[0:499]" -type "polyFaces" 
		f 3 0 1 2
		mu 0 3 0 1 2
		f 3 3 4 -3
		mu 0 3 2 3 0
		f 3 5 -5 6
		mu 0 3 4 0 3
		f 3 7 8 -7
		mu 0 3 3 5 4
		f 3 -8 9 10
		mu 0 3 5 3 6
		f 3 -11 11 12
		mu 0 3 5 6 7
		f 3 13 -12 14
		mu 0 3 8 7 6
		f 3 15 16 -15
		mu 0 3 6 9 8
		f 3 17 -17 18
		mu 0 3 10 8 9
		f 3 19 20 -19
		mu 0 3 9 11 10
		f 3 21 -21 22
		mu 0 3 12 10 11
		f 3 23 24 -23
		mu 0 3 11 13 12
		f 3 -25 25 26
		mu 0 3 12 13 14
		f 3 -27 27 28
		mu 0 3 12 14 15
		f 3 29 -29 30
		mu 0 3 16 12 15
		f 3 -31 31 32
		mu 0 3 16 15 17
		f 3 33 -33 34
		mu 0 3 18 16 17
		f 3 -35 35 36
		mu 0 3 18 17 19
		f 3 37 38 -37
		mu 0 3 19 20 18
		f 3 39 -39 40
		mu 0 3 21 18 20
		f 3 -41 41 42
		mu 0 3 21 20 22
		f 3 -42 43 44
		mu 0 3 22 20 23
		f 3 45 46 -44
		mu 0 3 20 24 23
		f 3 -47 47 48
		mu 0 3 23 24 25
		f 3 49 50 -48
		mu 0 3 24 26 25
		f 3 -51 51 52
		mu 0 3 25 26 27
		f 3 53 54 -52
		mu 0 3 26 28 27
		f 3 -55 55 56
		mu 0 3 27 28 29
		f 3 57 58 -56
		mu 0 3 28 30 29
		f 3 -59 59 60
		mu 0 3 29 30 31
		f 3 61 62 -60
		mu 0 3 30 32 31
		f 3 -63 63 64
		mu 0 3 31 32 33
		f 3 65 66 -64
		mu 0 3 32 34 33
		f 3 -67 67 68
		mu 0 3 33 34 35
		f 3 69 70 -68
		mu 0 3 34 36 35
		f 3 -71 71 72
		mu 0 3 35 36 37
		f 3 73 74 -72
		mu 0 3 36 38 37
		f 3 -75 75 76
		mu 0 3 37 38 39
		f 3 77 78 -76
		mu 0 3 38 40 39
		f 3 -79 79 80
		mu 0 3 39 40 41
		f 3 81 82 -80
		mu 0 3 40 42 41
		f 3 -83 83 84
		mu 0 3 41 42 43
		f 3 85 86 -84
		mu 0 3 42 44 43
		f 3 -87 87 88
		mu 0 3 43 44 45
		f 3 89 90 -88
		mu 0 3 44 46 45
		f 3 -91 91 92
		mu 0 3 45 46 47
		f 3 93 94 -92
		mu 0 3 46 48 47
		f 3 -95 95 96
		mu 0 3 47 48 49
		f 3 97 -96 98
		mu 0 3 50 49 48
		f 3 99 100 -99
		mu 0 3 48 51 50
		f 3 101 102 -101
		mu 0 3 51 52 50
		f 3 -103 103 104
		mu 0 3 50 52 53
		f 3 105 106 -104
		mu 0 3 52 54 53
		f 3 -107 107 108
		mu 0 3 53 54 55
		f 3 109 -109 110
		mu 0 3 56 53 55
		f 3 -111 111 112
		mu 0 3 56 55 57
		f 3 113 114 -112
		mu 0 3 55 58 57
		f 3 -115 115 116
		mu 0 3 57 58 59
		f 3 117 118 -116
		mu 0 3 58 60 59
		f 3 -119 119 120
		mu 0 3 59 60 61
		f 3 121 122 -120
		mu 0 3 60 62 61
		f 3 -123 123 124
		mu 0 3 61 62 63
		f 3 125 126 -124
		mu 0 3 62 64 63
		f 3 -127 127 128
		mu 0 3 63 64 65
		f 3 129 130 -128
		mu 0 3 64 66 65
		f 3 -131 131 132
		mu 0 3 65 66 67
		f 3 133 134 -132
		mu 0 3 66 68 67
		f 3 -135 135 136
		mu 0 3 67 68 69
		f 3 137 138 -136
		mu 0 3 68 70 69
		f 3 -139 139 140
		mu 0 3 69 70 71
		f 3 141 142 -140
		mu 0 3 70 72 71
		f 3 -143 143 144
		mu 0 3 71 72 73
		f 3 145 146 -144
		mu 0 3 72 74 73
		f 3 -147 147 148
		mu 0 3 73 74 75
		f 3 149 150 -148
		mu 0 3 74 76 75
		f 3 -151 151 152
		mu 0 3 75 76 77
		f 3 153 154 -152
		mu 0 3 76 78 77
		f 3 -155 155 156
		mu 0 3 77 78 79
		f 3 157 158 -156
		mu 0 3 78 80 79
		f 3 -159 159 160
		mu 0 3 79 80 81
		f 3 161 -160 162
		mu 0 3 82 81 80
		f 3 163 -163 164
		mu 0 3 83 82 80
		f 3 165 166 -165
		mu 0 3 80 84 83
		f 3 167 168 -167
		mu 0 3 84 85 83
		f 3 169 170 -169
		mu 0 3 85 86 83
		f 3 -171 171 172
		mu 0 3 83 86 87
		f 3 173 -172 174
		mu 0 3 88 87 86
		f 3 175 -175 176
		mu 0 3 89 88 86
		f 3 177 178 -177
		mu 0 3 86 90 89
		f 3 179 -179 180
		mu 0 3 91 89 90
		f 3 181 182 -181
		mu 0 3 90 92 91
		f 3 183 -183 184
		mu 0 3 93 91 92
		f 3 185 186 -185
		mu 0 3 92 94 93
		f 3 187 -187 188
		mu 0 3 95 93 94
		f 3 189 190 -189
		mu 0 3 94 96 95
		f 3 191 -191 192
		mu 0 3 97 95 96
		f 3 193 194 -193
		mu 0 3 96 98 97
		f 3 195 -195 196
		mu 0 3 99 97 98
		f 3 197 198 -197
		mu 0 3 98 100 99
		f 3 199 200 -199
		mu 0 3 100 101 99
		f 3 201 -201 202
		mu 0 3 102 99 101
		f 3 203 204 -203
		mu 0 3 101 103 102
		f 3 205 206 -205
		mu 0 3 103 104 102
		f 3 207 -207 208
		mu 0 3 105 102 104
		f 3 209 210 -209
		mu 0 3 104 106 105
		f 3 211 -211 212
		mu 0 3 107 105 106
		f 3 213 214 -213
		mu 0 3 106 108 107
		f 3 215 -215 216
		mu 0 3 109 107 108
		f 3 217 218 -217
		mu 0 3 108 110 109
		f 3 219 -219 220
		mu 0 3 111 109 110
		f 3 221 222 -221
		mu 0 3 110 112 111
		f 3 223 -223 224
		mu 0 3 113 111 112
		f 3 225 226 -225
		mu 0 3 112 114 113
		f 3 227 -227 228
		mu 0 3 115 113 114
		f 3 229 230 -229
		mu 0 3 114 116 115
		f 3 231 -231 232
		mu 0 3 117 115 116
		f 3 233 234 -233
		mu 0 3 116 118 117
		f 3 235 -235 236
		mu 0 3 119 117 118
		f 3 237 238 -237
		mu 0 3 118 120 119
		f 3 239 -239 240
		mu 0 3 121 119 120
		f 3 241 242 -241
		mu 0 3 120 122 121
		f 3 243 244 -243
		mu 0 3 122 123 121
		f 3 245 -245 246
		mu 0 3 124 121 123
		f 3 247 -247 248
		mu 0 3 125 124 123
		f 3 249 250 -249
		mu 0 3 123 126 125
		f 3 -250 251 252
		mu 0 3 126 123 127
		f 3 253 254 -253
		mu 0 3 127 128 126
		f 3 -254 255 256
		mu 0 3 128 127 129
		f 3 257 258 -256
		mu 0 3 127 130 129
		f 3 259 -259 260
		mu 0 3 131 129 130
		f 3 261 -261 262
		mu 0 3 132 131 130
		f 3 263 264 -263
		mu 0 3 130 133 132
		f 3 265 -265 266
		mu 0 3 134 132 133
		f 3 267 268 -267
		mu 0 3 133 135 134
		f 3 269 -269 270
		mu 0 3 136 134 135
		f 3 271 272 -271
		mu 0 3 135 137 136
		f 3 273 -273 274
		mu 0 3 138 136 137
		f 3 275 276 -275
		mu 0 3 137 139 138
		f 3 277 -277 278
		mu 0 3 140 138 139
		f 3 279 280 -279
		mu 0 3 139 141 140
		f 3 281 -281 282
		mu 0 3 142 140 141
		f 3 283 284 -283
		mu 0 3 141 143 142
		f 3 285 -285 286
		mu 0 3 144 142 143
		f 3 287 288 -287
		mu 0 3 143 145 144
		f 3 289 -289 290
		mu 0 3 146 144 145
		f 3 291 292 -291
		mu 0 3 145 147 146
		f 3 293 -293 294
		mu 0 3 148 146 147
		f 3 295 296 -295
		mu 0 3 147 149 148
		f 3 297 -297 298
		mu 0 3 150 148 149
		f 3 299 300 -299
		mu 0 3 149 151 150
		f 3 301 302 -301
		mu 0 3 151 152 150
		f 3 303 -303 304
		mu 0 3 153 150 152
		f 3 305 306 -305
		mu 0 3 152 154 153
		f 3 -307 307 308
		mu 0 3 153 154 155
		f 3 309 310 -308
		mu 0 3 154 156 155
		f 3 311 312 -311
		mu 0 3 156 157 155
		f 3 -313 313 314
		mu 0 3 155 157 158
		f 3 -314 315 316
		mu 0 3 158 157 159
		f 3 -317 317 318
		mu 0 3 158 159 160
		f 3 319 -318 320
		mu 0 3 161 160 159
		f 3 321 322 -321
		mu 0 3 159 162 161
		f 3 -323 323 324
		mu 0 3 161 162 163
		f 3 -325 325 326
		mu 0 3 161 163 164
		f 3 327 -326 328
		mu 0 3 165 164 163
		f 3 329 330 -329
		mu 0 3 163 166 165
		f 3 -331 331 332
		mu 0 3 165 166 167
		f 3 333 334 -332
		mu 0 3 166 168 167
		f 3 335 336 -335
		mu 0 3 168 169 167
		f 3 -337 337 338
		mu 0 3 167 169 170
		f 3 339 340 -339
		mu 0 3 170 171 167
		f 3 -340 341 342
		mu 0 3 171 170 172
		f 3 343 -343 344
		mu 0 3 173 171 172
		f 3 -345 345 346
		mu 0 3 173 172 174
		f 3 347 -346 348
		mu 0 3 175 174 172
		f 3 349 350 -349
		mu 0 3 172 176 175
		f 3 -351 351 352
		mu 0 3 175 176 177
		f 3 353 354 -352
		mu 0 3 176 178 177
		f 3 -355 355 356
		mu 0 3 177 178 179
		f 3 357 358 -356
		mu 0 3 178 180 179
		f 3 359 360 -359
		mu 0 3 180 181 179
		f 3 361 362 -361
		mu 0 3 181 182 179
		f 3 363 364 -362
		mu 0 3 181 183 182
		f 3 365 366 -365
		mu 0 3 183 184 182
		f 3 367 -367 368
		mu 0 3 185 182 184
		f 3 369 -369 370
		mu 0 3 186 185 184
		f 3 -371 371 372
		mu 0 3 186 184 187
		f 3 -373 373 374
		mu 0 3 186 187 188
		f 3 375 -375 376
		mu 0 3 189 186 188
		f 3 377 -377 378
		mu 0 3 190 189 188
		f 3 -379 379 380
		mu 0 3 190 188 191
		f 3 381 -380 382
		mu 0 3 192 191 188
		f 3 -382 383 384
		mu 0 3 191 192 193
		f 3 385 -384 386
		mu 0 3 194 193 192
		f 3 387 388 -387
		mu 0 3 192 195 194
		f 3 389 -389 390
		mu 0 3 196 194 195
		f 3 391 392 -391
		mu 0 3 195 197 196
		f 3 -392 393 394
		mu 0 3 197 195 198
		f 3 395 396 -395
		mu 0 3 198 199 197
		f 3 397 398 -396
		mu 0 3 198 200 199
		f 3 399 400 -399
		mu 0 3 200 201 199
		f 3 -400 401 402
		mu 0 3 201 200 202
		f 3 403 404 -402
		mu 0 3 200 203 202
		f 3 405 406 -405
		mu 0 3 203 204 202
		f 3 407 -407 408
		mu 0 3 205 202 204
		f 3 409 410 -409
		mu 0 3 204 206 205
		f 3 -410 411 412
		mu 0 3 206 204 207
		f 3 413 -412 414
		mu 0 3 208 207 204
		f 3 -414 415 416
		mu 0 3 207 208 209
		f 3 417 -416 418
		mu 0 3 210 209 208
		f 3 -419 419 420
		mu 0 3 210 208 211
		f 3 -421 421 422
		mu 0 3 210 211 212
		f 3 -422 423 424
		mu 0 3 212 211 213
		f 3 425 426 -424
		mu 0 3 211 214 213
		f 3 -427 427 428
		mu 0 3 213 214 215
		f 3 429 -428 430
		mu 0 3 216 215 214
		f 3 431 432 -431
		mu 0 3 214 217 216
		f 3 433 -433 434
		mu 0 3 218 216 217
		f 3 435 436 -435
		mu 0 3 217 219 218
		f 3 -437 437 438
		mu 0 3 218 219 220
		f 3 439 440 -438
		mu 0 3 219 221 220
		f 3 441 -441 442
		mu 0 3 222 220 221
		f 3 443 444 -443
		mu 0 3 221 223 222
		f 3 445 -445 446
		mu 0 3 224 222 223
		f 3 447 -447 448
		mu 0 3 225 224 223
		f 3 449 -449 450
		mu 0 3 178 225 223
		f 3 451 -448 452
		mu 0 3 169 224 225
		f 3 -452 453 454
		mu 0 3 224 169 226
		f 3 455 456 -455
		mu 0 3 226 227 224
		f 3 457 458 -456
		mu 0 3 226 228 227
		f 3 459 460 -459
		mu 0 3 228 229 227
		f 3 -461 461 462
		mu 0 3 227 229 230
		f 3 -463 463 464
		mu 0 3 227 230 222
		f 3 465 466 -462
		mu 0 3 229 231 230
		f 3 467 -467 468
		mu 0 3 232 230 231
		f 3 -468 469 470
		mu 0 3 230 232 220
		f 3 471 472 -466
		mu 0 3 229 233 231
		f 3 473 -472 474
		mu 0 3 234 233 229
		f 3 475 476 -474
		mu 0 3 234 235 233
		f 3 477 -476 478
		mu 0 3 236 235 234
		f 3 479 -479 480
		mu 0 3 237 236 234
		f 3 -481 481 482
		mu 0 3 237 234 228
		f 3 483 484 -483
		mu 0 3 228 238 237
		f 3 485 -485 486
		mu 0 3 239 237 238
		f 3 -487 487 488
		mu 0 3 239 238 240
		f 3 489 -489 490
		mu 0 3 241 239 240
		f 3 491 -491 492
		mu 0 3 242 241 240
		f 3 -493 493 494
		mu 0 3 242 240 166
		f 3 495 -492 496
		mu 0 3 243 241 242
		f 3 497 498 -497
		mu 0 3 242 162 243
		f 3 499 -499 500
		mu 0 3 244 243 162
		f 3 501 502 -500
		mu 0 3 244 245 243
		f 3 503 504 -503
		mu 0 3 245 246 243
		f 3 -504 505 506
		mu 0 3 246 245 247
		f 3 -506 507 508
		mu 0 3 247 245 248
		f 3 509 510 -509
		mu 0 3 248 249 247
		f 3 511 512 -511
		mu 0 3 249 250 247
		f 3 513 514 -513
		mu 0 3 250 251 247
		f 3 515 -514 516
		mu 0 3 252 251 250
		f 3 517 518 -517
		mu 0 3 250 253 252
		f 3 519 520 -519
		mu 0 3 253 254 252
		f 3 521 -521 522
		mu 0 3 255 252 254
		f 3 523 -523 524
		mu 0 3 256 255 254
		f 3 525 526 -525
		mu 0 3 254 257 256
		f 3 -526 527 528
		mu 0 3 257 254 258
		f 3 529 530 -529
		mu 0 3 258 259 257
		f 3 -530 531 532
		mu 0 3 259 258 260
		f 3 533 534 -532
		mu 0 3 258 261 260
		f 3 535 -535 536
		mu 0 3 262 260 261
		f 3 537 -537 538
		mu 0 3 263 262 261
		f 3 539 540 -539
		mu 0 3 261 264 263
		f 3 541 -541 542
		mu 0 3 265 263 264
		f 3 543 544 -543
		mu 0 3 264 249 265
		f 3 -545 545 546
		mu 0 3 265 249 266
		f 3 547 -547 548
		mu 0 3 267 265 266
		f 3 549 -549 550
		mu 0 3 268 267 266
		f 3 551 552 -551
		mu 0 3 266 269 268
		f 3 -553 553 554
		mu 0 3 268 269 270
		f 3 555 -555 556
		mu 0 3 271 268 270
		f 3 557 -557 558
		mu 0 3 272 271 270
		f 3 -559 559 560
		mu 0 3 272 270 154
		f 3 561 -558 562
		mu 0 3 273 271 272
		f 3 563 564 -563
		mu 0 3 272 274 273
		f 3 565 -565 566
		mu 0 3 275 273 274
		f 3 -567 567 568
		mu 0 3 275 274 103
		f 3 569 -569 570
		mu 0 3 276 275 103
		f 3 -570 571 572
		mu 0 3 275 276 277
		f 3 573 -572 574
		mu 0 3 278 277 276
		f 3 -575 575 576
		mu 0 3 278 276 279
		f 3 577 -577 578
		mu 0 3 280 278 279
		f 3 579 -579 580
		mu 0 3 281 280 279
		f 3 -581 581 582
		mu 0 3 281 279 100
		f 3 583 -583 584
		mu 0 3 282 281 100
		f 3 -584 585 586
		mu 0 3 281 282 283
		f 3 587 588 -587
		mu 0 3 283 284 281
		f 3 -588 589 590
		mu 0 3 284 283 285
		f 3 591 592 -591
		mu 0 3 285 286 284
		f 3 593 -593 594
		mu 0 3 287 284 286
		f 3 595 596 -595
		mu 0 3 286 288 287
		f 3 597 598 -597
		mu 0 3 288 289 287
		f 3 599 600 -599
		mu 0 3 289 290 287
		f 3 -601 601 602
		mu 0 3 287 290 291
		f 3 -602 603 604
		mu 0 3 291 290 292
		f 3 605 606 -604
		mu 0 3 290 293 292
		f 3 607 608 -607
		mu 0 3 293 294 292
		f 3 -609 609 610
		mu 0 3 292 294 278
		f 3 611 612 -608
		mu 0 3 293 295 294
		f 3 613 -613 614
		mu 0 3 296 294 295
		f 3 615 616 -615
		mu 0 3 295 297 296
		f 3 -617 617 618
		mu 0 3 296 297 298
		f 3 619 620 -618
		mu 0 3 297 299 298
		f 3 621 622 -621
		mu 0 3 299 300 298
		f 3 -623 623 624
		mu 0 3 298 300 301
		f 3 625 626 -625
		mu 0 3 301 302 298
		f 3 -626 627 628
		mu 0 3 302 301 273
		f 3 -624 629 630
		mu 0 3 301 300 303
		f 3 631 632 -630
		mu 0 3 300 304 303
		f 3 633 634 -633
		mu 0 3 304 267 303
		f 3 635 636 -634
		mu 0 3 304 305 267
		f 3 637 638 -636
		mu 0 3 304 306 305
		f 3 639 640 -639
		mu 0 3 306 307 305
		f 3 641 642 -641
		mu 0 3 307 263 305
		f 3 -640 643 644
		mu 0 3 307 306 308
		f 3 645 -644 646
		mu 0 3 309 308 306
		f 3 -647 647 648
		mu 0 3 309 306 310
		f 3 649 -649 650
		mu 0 3 311 309 310
		f 3 651 -651 652
		mu 0 3 299 311 310
		f 3 653 -652 654
		mu 0 3 312 311 299
		f 3 655 -654 656
		mu 0 3 313 311 312
		f 3 657 -657 658
		mu 0 3 314 313 312
		f 3 659 -659 660
		mu 0 3 315 314 312
		f 3 -661 661 662
		mu 0 3 315 312 297
		f 3 663 -660 664
		mu 0 3 316 314 315
		f 3 665 666 -665
		mu 0 3 315 317 316
		f 3 667 -667 668
		mu 0 3 318 316 317
		f 3 -669 669 670
		mu 0 3 318 317 319
		f 3 671 -671 672
		mu 0 3 320 318 319
		f 3 673 -673 674
		mu 0 3 289 320 319
		f 3 675 -674 676
		mu 0 3 321 320 289
		f 3 677 -676 678
		mu 0 3 322 320 321
		f 3 679 -679 680
		mu 0 3 323 322 321
		f 3 681 -681 682
		mu 0 3 324 323 321
		f 3 -683 683 684
		mu 0 3 324 321 288
		f 3 685 -685 686
		mu 0 3 325 324 288
		f 3 -686 687 688
		mu 0 3 324 325 326
		f 3 689 690 -689
		mu 0 3 326 327 324
		f 3 -690 691 692
		mu 0 3 327 326 328
		f 3 693 694 -693
		mu 0 3 328 329 327
		f 3 695 696 -695
		mu 0 3 329 330 327
		f 3 697 698 -697
		mu 0 3 330 323 327
		f 3 699 700 -698
		mu 0 3 330 331 323
		f 3 701 702 -700
		mu 0 3 330 332 331
		f 3 703 704 -703
		mu 0 3 332 333 331
		f 3 705 706 -705
		mu 0 3 333 334 331
		f 3 -707 707 708
		mu 0 3 331 334 322
		f 3 -708 709 710
		mu 0 3 322 334 335
		f 3 711 712 -710
		mu 0 3 334 336 335
		f 3 713 714 -713
		mu 0 3 336 337 335
		f 3 -715 715 716
		mu 0 3 335 337 318
		f 3 717 718 -714
		mu 0 3 336 338 337
		f 3 719 -719 720
		mu 0 3 339 337 338
		f 3 721 722 -721
		mu 0 3 338 340 339
		f 3 -723 723 724
		mu 0 3 339 340 341
		f 3 725 726 -724
		mu 0 3 340 342 341
		f 3 727 728 -727
		mu 0 3 342 343 341
		f 3 -729 729 730
		mu 0 3 341 343 313
		f 3 -730 731 732
		mu 0 3 313 343 344
		f 3 733 734 -732
		mu 0 3 343 345 344
		f 3 735 -735 736
		mu 0 3 346 344 345
		f 3 737 738 -737
		mu 0 3 345 347 346
		f 3 739 -739 740
		mu 0 3 348 346 347
		f 3 741 742 -741
		mu 0 3 347 349 348
		f 3 743 -743 744
		mu 0 3 350 348 349
		f 3 745 -745 746
		mu 0 3 351 350 349
		f 3 747 748 -747
		mu 0 3 349 352 351
		f 3 -748 749 750
		mu 0 3 352 349 353
		f 3 751 752 -751
		mu 0 3 353 354 352
		f 3 -752 753 754
		mu 0 3 354 353 355
		f 3 755 756 -754
		mu 0 3 353 356 355
		f 3 757 -757 758
		mu 0 3 357 355 356
		f 3 759 760 -759
		mu 0 3 356 358 357
		f 3 761 -761 762
		mu 0 3 359 357 358
		f 3 763 -763 764
		mu 0 3 342 359 358
		f 3 765 -764 766
		mu 0 3 360 359 342
		f 3 767 -766 768
		mu 0 3 361 359 360
		f 3 769 -769 770
		mu 0 3 362 361 360
		f 3 771 -771 772
		mu 0 3 363 362 360
		f 3 -773 773 774
		mu 0 3 363 360 340
		f 3 775 -772 776
		mu 0 3 364 362 363
		f 3 777 778 -777
		mu 0 3 363 365 364
		f 3 779 -779 780
		mu 0 3 366 364 365
		f 3 -781 781 782
		mu 0 3 366 365 367
		f 3 783 -783 784
		mu 0 3 368 366 367
		f 3 785 -785 786
		mu 0 3 333 368 367
		f 3 787 -786 788
		mu 0 3 369 368 333
		f 3 789 790 -788
		mu 0 3 369 370 368
		f 3 791 792 -791
		mu 0 3 370 371 368
		f 3 -792 793 794
		mu 0 3 371 370 372
		f 3 795 -794 796
		mu 0 3 373 372 370
		f 3 797 -797 798
		mu 0 3 374 373 370
		f 3 799 -798 800
		mu 0 3 375 373 374
		f 3 801 802 -801
		mu 0 3 374 376 375
		f 3 803 -803 804
		mu 0 3 377 375 376
		f 3 805 -805 806
		mu 0 3 378 377 376
		f 3 -807 807 808
		mu 0 3 378 376 379
		f 3 809 810 -809
		mu 0 3 379 380 378
		f 3 811 -811 812
		mu 0 3 381 378 380
		f 3 813 -813 814
		mu 0 3 382 381 380
		f 3 -815 815 816
		mu 0 3 382 380 383
		f 3 -816 817 818
		mu 0 3 383 380 384
		f 3 -819 819 820
		mu 0 3 383 384 385
		f 3 -820 821 822
		mu 0 3 385 384 329
		f 3 823 824 -822
		mu 0 3 384 386 329
		f 3 -824 825 826
		mu 0 3 386 384 379
		f 3 827 828 -827
		mu 0 3 379 387 386
		f 3 -829 829 830
		mu 0 3 386 387 332
		f 3 831 832 -830
		mu 0 3 387 369 332
		f 3 -832 833 834
		mu 0 3 369 387 374
		f 3 -823 835 836
		mu 0 3 385 329 388
		f 3 837 -837 838
		mu 0 3 389 385 388
		f 3 839 840 -839
		mu 0 3 388 390 389
		f 3 -841 841 842
		mu 0 3 389 390 391
		f 3 -842 843 844
		mu 0 3 391 390 392
		f 3 845 846 -844
		mu 0 3 390 393 392
		f 3 -847 847 848
		mu 0 3 392 393 394
		f 3 849 850 -848
		mu 0 3 393 395 394
		f 3 -851 851 852
		mu 0 3 394 395 396
		f 3 853 -853 854
		mu 0 3 397 394 396
		f 3 -855 855 856
		mu 0 3 397 396 398
		f 3 857 858 -856
		mu 0 3 396 399 398
		f 3 -859 859 860
		mu 0 3 398 399 400
		f 3 861 862 -860
		mu 0 3 399 401 400
		f 3 863 864 -863
		mu 0 3 401 402 400
		f 3 865 -865 866
		mu 0 3 403 400 402
		f 3 867 868 -867
		mu 0 3 402 404 403
		f 3 -869 869 870
		mu 0 3 403 404 405
		f 3 -870 871 872
		mu 0 3 405 404 406
		f 3 873 874 -872
		mu 0 3 404 407 406
		f 3 -875 875 876
		mu 0 3 406 407 408
		f 3 877 878 -876
		mu 0 3 407 409 408
		f 3 -879 879 880
		mu 0 3 408 409 410
		f 3 881 882 -880
		mu 0 3 409 92 410
		f 3 883 -881 884
		mu 0 3 411 408 410
		f 3 885 886 -885
		mu 0 3 410 85 411
		f 3 -886 887 888
		mu 0 3 85 410 90
		f 3 -884 889 890
		mu 0 3 408 411 412
		f 3 -890 891 892
		mu 0 3 412 411 413
		f 3 -892 893 894
		mu 0 3 413 411 84
		f 3 895 -895 896
		mu 0 3 78 413 84
		f 3 897 -893 898
		mu 0 3 414 412 413
		f 3 899 -899 900
		mu 0 3 76 414 413
		f 3 901 -898 902
		mu 0 3 415 412 414
		f 3 903 -903 904
		mu 0 3 416 415 414
		f 3 905 -905 906
		mu 0 3 74 416 414
		f 3 907 -904 908
		mu 0 3 417 415 416
		f 3 909 -909 910
		mu 0 3 418 417 416
		f 3 911 -911 912
		mu 0 3 72 418 416
		f 3 913 -910 914
		mu 0 3 419 417 418
		f 3 915 -915 916
		mu 0 3 420 419 418
		f 3 917 -917 918
		mu 0 3 70 420 418
		f 3 919 -916 920
		mu 0 3 421 419 420
		f 3 921 -921 922
		mu 0 3 422 421 420
		f 3 923 -923 924
		mu 0 3 68 422 420
		f 3 925 -922 926
		mu 0 3 423 421 422
		f 3 927 -927 928
		mu 0 3 424 423 422
		f 3 929 -929 930
		mu 0 3 66 424 422
		f 3 931 -928 932
		mu 0 3 425 423 424
		f 3 933 -933 934
		mu 0 3 426 425 424
		f 3 935 -935 936
		mu 0 3 64 426 424
		f 3 937 -934 938
		mu 0 3 427 425 426
		f 3 939 -939 940
		mu 0 3 428 427 426
		f 3 941 -941 942
		mu 0 3 62 428 426
		f 3 943 -940 944
		mu 0 3 429 427 428
		f 3 945 -945 946
		mu 0 3 430 429 428
		f 3 947 -947 948
		mu 0 3 60 430 428
		f 3 949 950 -946
		mu 0 3 430 431 429
		f 3 951 952 -951
		mu 0 3 431 432 429
		f 3 953 954 -953
		mu 0 3 432 433 429
		f 3 955 -954 956
		mu 0 3 434 433 432
		f 3 957 958 -957
		mu 0 3 432 435 434
		f 3 959 960 -959
		mu 0 3 435 436 434
		f 3 961 962 -961
		mu 0 3 436 437 434
		f 3 -963 963 964
		mu 0 3 434 437 438
		f 3 965 966 -964
		mu 0 3 437 439 438
		f 3 -967 967 968
		mu 0 3 438 439 440
		f 3 969 -969 970
		mu 0 3 441 438 440
		f 3 -971 971 972
		mu 0 3 441 440 442
		f 3 973 974 -972
		mu 0 3 440 443 442
		f 3 -975 975 976
		mu 0 3 442 443 444
		f 3 977 978 -976
		mu 0 3 443 445 444
		f 3 -979 979 980
		mu 0 3 444 445 446
		f 3 981 982 -980
		mu 0 3 445 447 446
		f 3 -983 983 984
		mu 0 3 446 447 448
		f 3 985 -984 986
		mu 0 3 403 448 447
		f 3 987 -985 988
		mu 0 3 419 446 448
		f 3 989 -982 990
		mu 0 3 398 447 445
		f 3 991 -981 992
		mu 0 3 421 444 446
		f 3 993 -978 994
		mu 0 3 397 445 443
		f 3 995 996 -995
		mu 0 3 443 449 397
		f 3 997 -977 998
		mu 0 3 423 442 444
		f 3 -996 -974 999
		mu 0 3 449 443 440;
	setAttr ".fc[500:999]"
		f 3 1000 -973 1001
		mu 0 3 425 441 442
		f 3 -970 1002 1003
		mu 0 3 438 441 433
		f 3 1004 -1003 1005
		mu 0 3 427 433 441
		f 3 1006 -1000 -968
		mu 0 3 439 449 440
		f 3 1007 -1007 1008
		mu 0 3 392 449 439
		f 3 1009 -966 1010
		mu 0 3 391 439 437
		f 3 1011 1012 -1011
		mu 0 3 437 450 391
		f 3 -1012 -962 1013
		mu 0 3 450 437 436
		f 3 1014 1015 -1014
		mu 0 3 436 451 450
		f 3 1016 1017 -1016
		mu 0 3 451 452 450
		f 3 1018 1019 -1018
		mu 0 3 452 389 450
		f 3 1020 -1017 1021
		mu 0 3 453 452 451
		f 3 1022 -1022 1023
		mu 0 3 454 453 451
		f 3 1024 -1024 1025
		mu 0 3 455 454 451
		f 3 -1025 1026 1027
		mu 0 3 454 455 456
		f 3 -1027 1028 1029
		mu 0 3 456 455 457
		f 3 -1029 1030 1031
		mu 0 3 457 455 435
		f 3 1032 -1032 1033
		mu 0 3 458 457 435
		f 3 -1033 1034 1035
		mu 0 3 457 458 459
		f 3 -1035 1036 1037
		mu 0 3 459 458 460
		f 3 -1037 1038 1039
		mu 0 3 460 458 431
		f 3 1040 -1040 1041
		mu 0 3 461 460 431
		f 3 -1041 1042 1043
		mu 0 3 460 461 54
		f 3 1044 1045 -1044
		mu 0 3 54 462 460
		f 3 1046 -1038 -1046
		mu 0 3 462 459 460
		f 3 1047 -1047 1048
		mu 0 3 463 459 462
		f 3 1049 -1049 1050
		mu 0 3 464 463 462
		f 3 1051 -1051 1052
		mu 0 3 52 464 462
		f 3 1053 -1050 1054
		mu 0 3 465 463 464
		f 3 1055 -1055 1056
		mu 0 3 466 465 464
		f 3 1057 -1057 1058
		mu 0 3 51 466 464
		f 3 -1058 1059 1060
		mu 0 3 466 51 467
		f 3 1061 1062 -1061
		mu 0 3 467 468 466
		f 3 1063 1064 -1063
		mu 0 3 468 469 466
		f 3 1065 -1064 1066
		mu 0 3 470 469 468
		f 3 1067 -1067 1068
		mu 0 3 471 470 468
		f 3 -1069 1069 1070
		mu 0 3 471 468 472
		f 3 -1070 1071 1072
		mu 0 3 472 468 473
		f 3 1073 1074 -1073
		mu 0 3 473 42 472
		f 3 1075 -1071 1076
		mu 0 3 474 471 472
		f 3 1077 1078 -1077
		mu 0 3 472 40 474
		f 3 1079 -1076 1080
		mu 0 3 475 471 474
		f 3 1081 -1081 1082
		mu 0 3 476 475 474
		f 3 1083 1084 -1083
		mu 0 3 474 38 476
		f 3 1085 -1082 1086
		mu 0 3 477 475 476
		f 3 1087 -1087 1088
		mu 0 3 478 477 476
		f 3 1089 1090 -1089
		mu 0 3 476 36 478
		f 3 1091 -1088 1092
		mu 0 3 479 477 478
		f 3 1093 -1093 1094
		mu 0 3 480 479 478
		f 3 1095 1096 -1095
		mu 0 3 478 34 480
		f 3 1097 -1094 1098
		mu 0 3 481 479 480
		f 3 1099 -1099 1100
		mu 0 3 482 481 480
		f 3 1101 1102 -1101
		mu 0 3 480 32 482
		f 3 1103 -1100 1104
		mu 0 3 483 481 482
		f 3 1105 -1105 1106
		mu 0 3 484 483 482
		f 3 1107 1108 -1107
		mu 0 3 482 30 484
		f 3 1109 -1106 1110
		mu 0 3 485 483 484
		f 3 1111 -1111 1112
		mu 0 3 486 485 484
		f 3 1113 1114 -1113
		mu 0 3 484 28 486
		f 3 1115 -1112 1116
		mu 0 3 487 485 486
		f 3 1117 -1117 1118
		mu 0 3 488 487 486
		f 3 1119 1120 -1119
		mu 0 3 486 26 488
		f 3 1121 -1118 1122
		mu 0 3 489 487 488
		f 3 1123 -1123 1124
		mu 0 3 19 489 488
		f 3 1125 1126 -1125
		mu 0 3 488 24 19
		f 3 1127 1128 -1122
		mu 0 3 489 490 487
		f 3 1129 -1129 1130
		mu 0 3 491 487 490
		f 3 1131 1132 -1131
		mu 0 3 490 492 491
		f 3 1133 1134 -1133
		mu 0 3 492 493 491
		f 3 -1135 1135 1136
		mu 0 3 491 493 494
		f 3 1137 1138 -1136
		mu 0 3 493 495 494
		f 3 -1139 1139 1140
		mu 0 3 494 495 496
		f 3 1141 1142 -1140
		mu 0 3 495 497 496
		f 3 -1143 1143 1144
		mu 0 3 496 497 498
		f 3 1145 1146 -1144
		mu 0 3 497 499 498
		f 3 -1147 1147 1148
		mu 0 3 498 499 500
		f 3 1149 1150 -1148
		mu 0 3 499 501 500
		f 3 -1151 1151 1152
		mu 0 3 500 501 502
		f 3 1153 1154 -1152
		mu 0 3 501 503 502
		f 3 -1155 1155 1156
		mu 0 3 502 503 470
		f 3 1157 1158 -1157
		mu 0 3 470 475 502
		f 3 1159 1160 -1154
		mu 0 3 501 504 503
		f 3 -1161 1161 1162
		mu 0 3 503 504 505
		f 3 1163 1164 -1162
		mu 0 3 504 506 505
		f 3 -1165 1165 1166
		mu 0 3 505 506 507
		f 3 1167 1168 -1166
		mu 0 3 506 508 507
		f 3 -1169 1169 1170
		mu 0 3 507 508 509
		f 3 1171 1172 -1170
		mu 0 3 508 456 509
		f 3 1173 -1172 1174
		mu 0 3 510 456 508
		f 3 1175 1176 -1175
		mu 0 3 508 511 510
		f 3 1177 1178 -1177
		mu 0 3 511 512 510
		f 3 -1179 1179 1180
		mu 0 3 510 512 454
		f 3 -1178 1181 1182
		mu 0 3 512 511 513
		f 3 1183 1184 -1183
		mu 0 3 513 382 512
		f 3 1185 -1184 1186
		mu 0 3 514 382 513
		f 3 1187 -1187 1188
		mu 0 3 515 514 513
		f 3 1189 1190 -1189
		mu 0 3 513 516 515
		f 3 1191 -1191 1192
		mu 0 3 517 515 516
		f 3 -1193 1193 1194
		mu 0 3 517 516 518
		f 3 -1194 1195 1196
		mu 0 3 518 516 504
		f 3 1197 1198 -1196
		mu 0 3 516 511 504
		f 3 1199 -1195 1200
		mu 0 3 519 517 518
		f 3 1201 1202 -1201
		mu 0 3 518 499 519
		f 3 1203 -1200 1204
		mu 0 3 520 517 519
		f 3 1205 -1205 1206
		mu 0 3 521 520 519
		f 3 1207 1208 -1207
		mu 0 3 519 497 521
		f 3 1209 -1206 1210
		mu 0 3 522 520 521
		f 3 1211 -1211 1212
		mu 0 3 523 522 521
		f 3 1213 1214 -1213
		mu 0 3 521 495 523
		f 3 1215 -1212 1216
		mu 0 3 524 522 523
		f 3 1217 -1217 1218
		mu 0 3 525 524 523
		f 3 1219 1220 -1219
		mu 0 3 523 493 525
		f 3 -1218 1221 1222
		mu 0 3 524 525 526
		f 3 1223 -1222 1224
		mu 0 3 527 526 525
		f 3 1225 -1225 1226
		mu 0 3 492 527 525
		f 3 1227 -1226 1228
		mu 0 3 528 527 492
		f 3 -1228 1229 1230
		mu 0 3 527 528 529
		f 3 1231 -1230 1232
		mu 0 3 530 529 528
		f 3 1233 -1233 1234
		mu 0 3 531 530 528
		f 3 -1235 1235 1236
		mu 0 3 531 528 490
		f 3 1237 -1234 1238
		mu 0 3 15 530 531
		f 3 1239 1240 -1232
		mu 0 3 530 532 529
		f 3 1241 1242 -1241
		mu 0 3 532 533 529
		f 3 1243 -1243 1244
		mu 0 3 534 529 533
		f 3 1245 1246 -1245
		mu 0 3 533 535 534
		f 3 -1247 1247 1248
		mu 0 3 534 535 536
		f 3 -1249 1249 1250
		mu 0 3 534 536 526
		f 3 1251 -1250 1252
		mu 0 3 537 526 536
		f 3 1253 1254 -1253
		mu 0 3 536 538 537
		f 3 -1255 1255 1256
		mu 0 3 537 538 539
		f 3 -1257 1257 1258
		mu 0 3 537 539 540
		f 3 1259 -1259 1260
		mu 0 3 524 537 540
		f 3 1261 -1258 1262
		mu 0 3 541 540 539
		f 3 1263 1264 -1263
		mu 0 3 539 542 541
		f 3 1265 -1265 1266
		mu 0 3 543 541 542
		f 3 1267 1268 -1267
		mu 0 3 542 544 543
		f 3 -1269 1269 1270
		mu 0 3 543 544 545
		f 3 1271 1272 -1270
		mu 0 3 544 546 545
		f 3 1273 -1273 1274
		mu 0 3 547 545 546
		f 3 1275 1276 -1275
		mu 0 3 546 548 547
		f 3 1277 -1277 1278
		mu 0 3 549 547 548
		f 3 1279 1280 -1279
		mu 0 3 548 550 549
		f 3 -1281 1281 1282
		mu 0 3 549 550 551
		f 3 1283 1284 -1282
		mu 0 3 550 552 551
		f 3 1285 -1285 1286
		mu 0 3 553 551 552
		f 3 1287 1288 -1287
		mu 0 3 552 554 553
		f 3 -1289 1289 1290
		mu 0 3 553 554 555
		f 3 1291 1292 -1290
		mu 0 3 554 556 555
		f 3 1293 -1293 1294
		mu 0 3 557 555 556
		f 3 1295 1296 -1295
		mu 0 3 556 558 557
		f 3 -1297 1297 1298
		mu 0 3 557 558 559
		f 3 1299 1300 -1298
		mu 0 3 558 560 559
		f 3 1301 -1301 1302
		mu 0 3 561 559 560
		f 3 1303 -1303 1304
		mu 0 3 562 561 560
		f 3 1305 1306 -1305
		mu 0 3 560 563 562
		f 3 -1306 1307 1308
		mu 0 3 563 560 564
		f 3 1309 1310 -1309
		mu 0 3 564 565 563
		f 3 -1310 1311 1312
		mu 0 3 565 564 566
		f 3 1313 1314 -1312
		mu 0 3 564 567 566
		f 3 1315 -1315 1316
		mu 0 3 568 566 567
		f 3 1317 -1317 1318
		mu 0 3 569 568 567
		f 3 -1319 1319 1320
		mu 0 3 569 567 556
		f 3 1321 -1318 1322
		mu 0 3 570 568 569
		f 3 1323 1324 -1323
		mu 0 3 569 571 570
		f 3 1325 -1325 1326
		mu 0 3 572 570 571
		f 3 1327 -1327 1328
		mu 0 3 573 572 571
		f 3 -1329 1329 1330
		mu 0 3 573 571 552
		f 3 1331 -1328 1332
		mu 0 3 574 572 573
		f 3 1333 1334 -1333
		mu 0 3 573 575 574
		f 3 1335 -1335 1336
		mu 0 3 576 574 575
		f 3 1337 -1337 1338
		mu 0 3 577 576 575
		f 3 -1339 1339 1340
		mu 0 3 577 575 548
		f 3 1341 -1338 1342
		mu 0 3 578 576 577
		f 3 1343 -1343 1344
		mu 0 3 579 578 577
		f 3 -1345 1345 1346
		mu 0 3 579 577 546
		f 3 1347 -1344 1348
		mu 0 3 580 578 579
		f 3 1349 1350 -1349
		mu 0 3 579 581 580
		f 3 1351 -1351 1352
		mu 0 3 582 580 581
		f 3 1353 -1353 1354
		mu 0 3 583 582 581
		f 3 -1355 1355 1356
		mu 0 3 583 581 542
		f 3 1357 -1354 1358
		mu 0 3 584 582 583
		f 3 1359 -1359 1360
		mu 0 3 538 584 583
		f 3 1361 -1360 1362
		mu 0 3 585 584 538
		f 3 -1362 1363 1364
		mu 0 3 584 585 586
		f 3 1365 -1364 1366
		mu 0 3 587 586 585
		f 3 1367 -1367 1368
		mu 0 3 535 587 585
		f 3 1369 -1368 1370
		mu 0 3 588 587 535
		f 3 -1370 1371 1372
		mu 0 3 587 588 589
		f 3 1373 -1372 1374
		mu 0 3 590 589 588
		f 3 1375 -1375 1376
		mu 0 3 591 590 588
		f 3 -1377 1377 1378
		mu 0 3 591 588 533
		f 3 1379 -1376 1380
		mu 0 3 592 590 591
		f 3 1381 1382 -1381
		mu 0 3 591 593 592
		f 3 1383 -1383 1384
		mu 0 3 594 592 593
		f 3 1385 -1385 1386
		mu 0 3 13 594 593
		f 3 1387 -1386 1388
		mu 0 3 595 594 13
		f 3 -1388 1389 1390
		mu 0 3 594 595 596
		f 3 1391 -1390 1392
		mu 0 3 1 596 595
		f 3 1393 1394 -1392
		mu 0 3 1 597 596
		f 3 1395 1396 -1395
		mu 0 3 597 598 596
		f 3 1397 1398 -1397
		mu 0 3 598 599 596
		f 3 1399 1400 -1398
		mu 0 3 598 600 599
		f 3 1401 -1401 1402
		mu 0 3 601 599 600
		f 3 1403 1404 -1403
		mu 0 3 600 602 601
		f 3 1405 -1405 1406
		mu 0 3 603 601 602
		f 3 1407 1408 -1407
		mu 0 3 602 604 603
		f 3 -1409 1409 1410
		mu 0 3 603 604 605
		f 3 -1411 1411 1412
		mu 0 3 603 605 589
		f 3 1413 -1412 1414
		mu 0 3 606 589 605
		f 3 1415 1416 -1415
		mu 0 3 605 607 606
		f 3 -1417 1417 1418
		mu 0 3 606 607 608
		f 3 -1419 1419 1420
		mu 0 3 606 608 586
		f 3 1421 -1420 1422
		mu 0 3 609 586 608
		f 3 1423 1424 -1423
		mu 0 3 608 610 609
		f 3 1425 -1425 1426
		mu 0 3 611 609 610
		f 3 1427 1428 -1427
		mu 0 3 610 612 611
		f 3 -1429 1429 1430
		mu 0 3 611 612 613
		f 3 1431 1432 -1430
		mu 0 3 612 614 613
		f 3 1433 -1433 1434
		mu 0 3 615 613 614
		f 3 1435 1436 -1435
		mu 0 3 614 616 615
		f 3 1437 -1437 1438
		mu 0 3 617 615 616
		f 3 1439 1440 -1439
		mu 0 3 616 618 617
		f 3 -1441 1441 1442
		mu 0 3 617 618 619
		f 3 1443 1444 -1442
		mu 0 3 618 620 619
		f 3 1445 -1445 1446
		mu 0 3 621 619 620
		f 3 1447 1448 -1447
		mu 0 3 620 622 621
		f 3 -1449 1449 1450
		mu 0 3 621 622 623
		f 3 1451 1452 -1450
		mu 0 3 622 624 623
		f 3 1453 -1453 1454
		mu 0 3 625 623 624
		f 3 1455 -1455 1456
		mu 0 3 626 625 624
		f 3 1457 1458 -1457
		mu 0 3 624 627 626
		f 3 -1458 1459 1460
		mu 0 3 627 624 628
		f 3 1461 1462 -1461
		mu 0 3 628 629 627
		f 3 -1462 1463 1464
		mu 0 3 629 628 630
		f 3 1465 1466 -1464
		mu 0 3 628 631 630
		f 3 1467 1468 -1467
		mu 0 3 631 632 630
		f 3 1469 -1469 1470
		mu 0 3 633 630 632
		f 3 1471 1472 -1471
		mu 0 3 632 634 633
		f 3 -1472 1473 1474
		mu 0 3 634 632 635
		f 3 1475 -1474 1476
		mu 0 3 636 635 632
		f 3 -1476 1477 1478
		mu 0 3 635 636 637
		f 3 1479 1480 -1479
		mu 0 3 637 638 635
		f 3 1481 -1481 1482
		mu 0 3 639 635 638
		f 3 1483 1484 -1483
		mu 0 3 638 640 639
		f 3 -1484 1485 1486
		mu 0 3 640 638 641
		f 3 1487 1488 -1486
		mu 0 3 638 642 641
		f 3 -1488 1489 1490
		mu 0 3 642 638 643
		f 3 1491 1492 -1491
		mu 0 3 643 644 642
		f 3 1493 -1493 1494
		mu 0 3 645 642 644
		f 3 1495 1496 -1495
		mu 0 3 644 646 645
		f 3 1497 -1497 1498
		mu 0 3 647 645 646
		f 3 1499 -1499 1500
		mu 0 3 648 647 646
		f 3 -1501 1501 1502
		mu 0 3 648 646 649
		f 3 1503 1504 -1503
		mu 0 3 649 650 648
		f 3 1505 -1505 1506
		mu 0 3 651 648 650
		f 3 1507 -1507 1508
		mu 0 3 652 651 650
		f 3 -1509 1509 1510
		mu 0 3 652 650 653
		f 3 1511 1512 -1511
		mu 0 3 653 654 652
		f 3 1513 -1513 1514
		mu 0 3 655 652 654
		f 3 1515 1516 -1515
		mu 0 3 654 656 655
		f 3 1517 -1517 1518
		mu 0 3 657 655 656
		f 3 1519 -1519 1520
		mu 0 3 658 657 656
		f 3 -1521 1521 1522
		mu 0 3 658 656 659
		f 3 1523 -1523 1524
		mu 0 3 604 658 659
		f 3 1525 -1524 1526
		mu 0 3 660 658 604
		f 3 -1526 1527 1528
		mu 0 3 658 660 661
		f 3 1529 -1528 1530
		mu 0 3 662 661 660
		f 3 1531 -1531 1532
		mu 0 3 663 662 660
		f 3 -1533 1533 1534
		mu 0 3 663 660 602
		f 3 1535 -1532 1536
		mu 0 3 664 662 663
		f 3 1537 1538 -1537
		mu 0 3 663 665 664
		f 3 1539 -1539 1540
		mu 0 3 666 664 665
		f 3 1541 1542 -1541
		mu 0 3 665 667 666
		f 3 1543 -1543 1544
		mu 0 3 668 666 667
		f 3 -1545 1545 1546
		mu 0 3 668 667 597
		f 3 1547 -1547 1548
		mu 0 3 669 668 597
		f 3 1549 -1548 1550
		mu 0 3 670 668 669
		f 3 1551 1552 -1551
		mu 0 3 669 671 670
		f 3 -1552 1553 1554
		mu 0 3 671 669 672
		f 3 1555 1556 -1554
		mu 0 3 669 1 672
		f 3 1557 -1555 1558
		mu 0 3 673 671 672
		f 3 1559 1560 -1559
		mu 0 3 672 674 673
		f 3 -1560 1561 1562
		mu 0 3 674 672 0
		f 3 -1558 1563 1564
		mu 0 3 671 673 675
		f 3 -1550 1565 1566
		mu 0 3 668 670 676
		f 3 1567 -1567 1568
		mu 0 3 677 668 676
		f 3 1569 1570 -1568
		mu 0 3 677 678 668
		f 3 1571 -1570 1572
		mu 0 3 679 678 677
		f 3 1573 -1573 1574
		mu 0 3 680 679 677
		f 3 1575 1576 -1574
		mu 0 3 680 681 679
		f 3 1577 -1577 1578
		mu 0 3 682 679 681
		f 3 1579 1580 -1579
		mu 0 3 681 683 682
		f 3 -1581 1581 1582
		mu 0 3 682 683 684
		f 3 -1583 1583 1584
		mu 0 3 682 684 685
		f 3 1585 -1585 1586
		mu 0 3 686 682 685
		f 3 -1587 1587 1588
		mu 0 3 686 685 664
		f 3 1589 -1584 1590
		mu 0 3 687 685 684
		f 3 1591 1592 -1591
		mu 0 3 684 688 687
		f 3 -1593 1593 1594
		mu 0 3 687 688 689
		f 3 -1595 1595 1596
		mu 0 3 687 689 661
		f 3 1597 -1596 1598
		mu 0 3 657 661 689
		f 3 1599 1600 -1599
		mu 0 3 689 690 657
		f 3 -1600 1601 1602
		mu 0 3 690 689 691
		f 3 1603 1604 -1603
		mu 0 3 691 692 690
		f 3 -1605 1605 1606
		mu 0 3 690 692 693
		f 3 -1607 1607 1608
		mu 0 3 690 693 655
		f 3 1609 1610 -1606
		mu 0 3 692 694 693
		f 3 -1611 1611 1612
		mu 0 3 693 694 651
		f 3 1613 1614 -1612
		mu 0 3 694 695 651
		f 3 -1614 1615 1616
		mu 0 3 695 694 696
		f 3 1617 -1616 1618
		mu 0 3 697 696 694
		f 3 -1618 1619 1620
		mu 0 3 696 697 698
		f 3 1621 -1620 1622
		mu 0 3 699 698 697
		f 3 1623 -1623 1624
		mu 0 3 700 699 697
		f 3 -1625 1625 1626
		mu 0 3 700 697 692
		f 3 1627 -1624 1628
		mu 0 3 701 699 700
		f 3 1629 1630 -1629
		mu 0 3 700 702 701
		f 3 1631 -1631 1632
		mu 0 3 703 701 702
		f 3 1633 -1633 1634
		mu 0 3 704 703 702
		f 3 -1635 1635 1636
		mu 0 3 704 702 688
		f 3 -1636 1637 1638
		mu 0 3 688 702 691
		f 3 1639 -1634 1640
		mu 0 3 705 703 704
		f 3 1641 1642 -1641
		mu 0 3 704 683 705
		f 3 1643 -1643 1644
		mu 0 3 706 705 683
		f 3 1645 1646 -1644
		mu 0 3 706 707 705
		f 3 1647 1648 -1647
		mu 0 3 707 708 705
		f 3 -1648 1649 1650
		mu 0 3 708 707 709
		f 3 -1651 1651 1652
		mu 0 3 708 709 710
		f 3 -1653 1653 1654
		mu 0 3 708 710 711
		f 3 1655 1656 -1654
		mu 0 3 710 712 711
		f 3 1657 -1657 1658
		mu 0 3 713 711 712
		f 3 1659 1660 -1659
		mu 0 3 712 714 713
		f 3 1661 -1661 1662
		mu 0 3 715 713 714
		f 3 1663 1664 -1663
		mu 0 3 714 716 715
		f 3 -1665 1665 1666
		mu 0 3 715 716 717
		f 3 1667 1668 -1666
		mu 0 3 716 718 717
		f 3 1669 -1669 1670
		mu 0 3 719 717 718
		f 3 1671 1672 -1671
		mu 0 3 718 720 719
		f 3 1673 1674 -1673
		mu 0 3 720 721 719
		f 3 1675 1676 -1675
		mu 0 3 721 722 719
		f 3 -1676 1677 1678
		mu 0 3 722 721 723
		f 3 1679 -1679 1680
		mu 0 3 696 722 723
		f 3 1681 -1678 1682
		mu 0 3 724 723 721
		f 3 1683 -1683 1684
		mu 0 3 725 724 721
		f 3 -1684 1685 1686
		mu 0 3 724 725 726
		f 3 1687 1688 -1687
		mu 0 3 726 645 724
		f 3 -1688 1689 1690
		mu 0 3 645 726 727
		f 3 -1682 1691 1692
		mu 0 3 723 724 647
		f 3 1693 -1693 1694
		mu 0 3 695 723 647
		f 3 -1674 1695 -1685
		mu 0 3 721 720 725
		f 3 1696 1697 -1672
		mu 0 3 718 728 720
		f 3 1698 -1697 1699
		mu 0 3 729 728 718
		f 3 1700 1701 -1699
		mu 0 3 729 730 728
		f 3 1702 -1701 1703
		mu 0 3 731 730 729
		f 3 1704 1705 -1704
		mu 0 3 729 732 731
		f 3 1706 -1706 1707
		mu 0 3 733 731 732
		f 3 1708 -1708 1709
		mu 0 3 734 733 732
		f 3 -1710 1710 1711
		mu 0 3 734 732 714
		f 3 1712 -1709 1713
		mu 0 3 735 733 734
		f 3 1714 1715 -1714
		mu 0 3 734 736 735
		f 3 1716 1717 -1716
		mu 0 3 736 737 735
		f 3 1718 -1718 1719
		mu 0 3 738 735 737
		f 3 1720 -1720 1721
		mu 0 3 739 738 737
		f 3 1722 -1722 1723
		mu 0 3 740 739 737
		f 3 -1724 1724 1725
		mu 0 3 740 737 741
		f 3 1726 -1726 1727
		mu 0 3 742 740 741
		f 3 1728 1729 -1728
		mu 0 3 741 743 742
		f 3 -1729 1730 1731
		mu 0 3 743 741 744
		f 3 1732 -1731 1733
		mu 0 3 736 744 741
		f 3 -1733 1734 1735
		mu 0 3 744 736 710
		f 3 1736 1737 -1732
		mu 0 3 744 745 743
		f 3 -1737 1738 1739
		mu 0 3 745 744 709
		f 3 1740 1741 -1740
		mu 0 3 709 746 745
		f 3 1742 1743 -1721
		mu 0 3 739 747 738
		f 3 1744 1745 -1744
		mu 0 3 747 748 738
		f 3 1746 1747 -1746
		mu 0 3 748 749 738
		f 3 -1747 1748 1749
		mu 0 3 749 748 750
		f 3 1750 -1750 1751
		mu 0 3 751 749 750
		f 3 1752 1753 -1752
		mu 0 3 750 752 751
		f 3 1754 -1754 1755
		mu 0 3 753 751 752
		f 3 -1755 1756 1757
		mu 0 3 751 753 731
		f 3 -1753 1758 1759
		mu 0 3 752 750 754
		f 3 -1751 1760 1761
		mu 0 3 749 751 733
		f 3 1762 -1759 -1749
		mu 0 3 748 754 750
		f 3 -1763 1763 1764
		mu 0 3 754 748 755
		f 3 1765 -1764 -1745
		mu 0 3 747 755 748
		f 3 1766 1767 -1766
		mu 0 3 747 756 755
		f 3 -1719 -1748 1768
		mu 0 3 735 738 749
		f 3 -1717 -1734 -1725
		mu 0 3 737 736 741
		f 3 -1715 1769 1770
		mu 0 3 736 734 712
		f 3 -1769 -1762 -1713
		mu 0 3 735 749 733
		f 3 -1707 -1761 -1758
		mu 0 3 731 733 751
		f 3 -1705 1771 1772
		mu 0 3 732 729 716
		f 3 -1703 -1757 1773
		mu 0 3 730 731 753
		f 3 -1670 -1677 1774
		mu 0 3 717 719 722
		f 3 1775 -1775 1776
		mu 0 3 698 717 722
		f 3 -1668 -1772 -1700
		mu 0 3 718 716 729
		f 3 -1667 -1776 1777
		mu 0 3 715 717 698
		f 3 -1711 -1773 -1664
		mu 0 3 714 732 716
		f 3 -1662 1778 1779
		mu 0 3 713 715 699
		f 3 -1712 -1660 -1770
		mu 0 3 734 714 712
		f 3 -1658 1780 1781
		mu 0 3 711 713 701
		f 3 -1656 -1735 -1771
		mu 0 3 712 710 736
		f 3 -1655 1782 1783
		mu 0 3 708 711 703
		f 3 -1739 -1736 -1652
		mu 0 3 709 744 710
		f 3 -1741 -1650 1784
		mu 0 3 746 709 707
		f 3 1785 -1785 -1646
		mu 0 3 706 746 707
		f 3 1786 1787 -1786
		mu 0 3 706 681 746
		f 3 -1640 -1649 -1784
		mu 0 3 703 705 708
		f 3 -1632 -1783 -1782
		mu 0 3 701 703 711
		f 3 -1630 1788 -1638
		mu 0 3 702 700 691
		f 3 -1780 -1628 -1781
		mu 0 3 713 699 701
		f 3 -1622 -1779 -1778
		mu 0 3 698 699 715
		f 3 -1777 -1680 -1621
		mu 0 3 698 722 696
		f 3 -1681 -1694 -1617
		mu 0 3 696 723 695
		f 3 -1626 -1619 -1610
		mu 0 3 692 697 694
		f 3 -1627 -1604 -1789
		mu 0 3 700 692 691
		f 3 -1639 -1602 -1594
		mu 0 3 688 691 689
		f 3 -1592 1789 -1637
		mu 0 3 688 684 704
		f 3 -1590 1790 1791
		mu 0 3 685 687 662
		f 3 -1642 -1790 -1582
		mu 0 3 683 704 684
		f 3 -1580 -1787 -1645
		mu 0 3 683 681 706
		f 3 -1578 -1586 1792
		mu 0 3 679 682 686
		f 3 -1576 1793 -1788
		mu 0 3 681 680 746
		f 3 -1572 -1793 1794
		mu 0 3 678 679 686
		f 3 -1795 1795 1796
		mu 0 3 678 686 666
		f 3 -1544 -1571 -1797
		mu 0 3 666 668 678
		f 3 -1542 1797 1798
		mu 0 3 667 665 598
		f 3 -1540 -1796 -1589
		mu 0 3 664 666 686
		f 3 -1538 1799 1800
		mu 0 3 665 663 600
		f 3 -1536 -1588 -1792
		mu 0 3 662 664 685
		f 3 -1791 -1597 -1530
		mu 0 3 662 687 661
		f 3 1801 -1522 1802
		mu 0 3 757 659 656
		f 3 -1802 1803 1804
		mu 0 3 659 757 607
		f 3 -1804 1805 1806
		mu 0 3 607 757 758
		f 3 1807 1808 -1806
		mu 0 3 757 759 758
		f 3 -1809 1809 1810
		mu 0 3 758 759 760
		f 3 1811 1812 -1810
		mu 0 3 759 761 760
		f 3 1813 -1813 1814
		mu 0 3 762 760 761
		f 3 1815 1816 -1815
		mu 0 3 761 763 762
		f 3 -1817 1817 1818
		mu 0 3 762 763 764
		f 3 1819 1820 -1818
		mu 0 3 763 765 764
		f 3 1821 -1821 1822
		mu 0 3 766 764 765
		f 3 1823 1824 -1823
		mu 0 3 765 767 766
		f 3 1825 -1825 1826
		mu 0 3 768 766 767
		f 3 1827 1828 -1827
		mu 0 3 767 636 768
		f 3 -1829 1829 1830
		mu 0 3 768 636 631
		f 3 -1831 1831 1832
		mu 0 3 768 631 620
		f 3 -1826 1833 1834
		mu 0 3 766 768 618
		f 3 -1824 1835 1836
		mu 0 3 767 765 769
		f 3 1837 -1836 1838
		mu 0 3 770 769 765
		f 3 1839 1840 -1838
		mu 0 3 770 771 769
		f 3 1841 1842 -1841
		mu 0 3 771 643 769
		f 3 -1843 1843 1844
		mu 0 3 769 643 637
		f 3 1845 -1840 1846
		mu 0 3 649 771 770
		f 3 1847 1848 -1847
		mu 0 3 770 772 649
		f 3 -1848 1849 1850
		mu 0 3 772 770 763
		f 3 -1845 1851 -1837
		mu 0 3 769 637 767
		f 3 -1822 1852 1853
		mu 0 3 764 766 616
		f 3 -1820 -1850 -1839
		mu 0 3 765 763 770
		f 3 -1819 1854 1855
		mu 0 3 762 764 614
		f 3 1856 -1851 -1816
		mu 0 3 761 772 763
		f 3 1857 -1857 1858
		mu 0 3 653 772 761
		f 3 -1814 1859 1860
		mu 0 3 760 762 612
		f 3 -1812 1861 -1859
		mu 0 3 761 759 653
		f 3 -1811 1862 1863
		mu 0 3 758 760 610
		f 3 1864 1865 -1808
		mu 0 3 757 654 759
		f 3 -1598 -1520 -1529
		mu 0 3 661 657 658
		f 3 -1601 -1609 -1518
		mu 0 3 657 690 655
		f 3 -1516 -1865 -1803
		mu 0 3 656 654 757
		f 3 -1514 -1608 1866
		mu 0 3 652 655 693
		f 3 -1512 -1862 -1866
		mu 0 3 654 653 759
		f 3 -1510 1867 -1858
		mu 0 3 653 650 772
		f 3 -1613 -1508 -1867
		mu 0 3 693 651 652
		f 3 -1506 -1615 1868
		mu 0 3 648 651 695
		f 3 -1504 -1849 -1868
		mu 0 3 650 649 772
		f 3 -1502 1869 -1846
		mu 0 3 649 646 771
		f 3 -1695 -1500 -1869
		mu 0 3 695 647 648
		f 3 -1498 -1692 -1689
		mu 0 3 645 647 724
		f 3 -1496 1870 -1870
		mu 0 3 646 644 771
		f 3 -1691 1871 -1494
		mu 0 3 645 727 642
		f 3 -1842 -1871 -1492
		mu 0 3 643 771 644
		f 3 -1480 -1844 -1490
		mu 0 3 638 637 643
		f 3 -1852 -1478 -1828
		mu 0 3 767 637 636
		f 3 -1482 1872 -1475
		mu 0 3 635 639 634
		f 3 -1468 -1830 -1477
		mu 0 3 632 631 636
		f 3 -1466 1873 1874
		mu 0 3 631 628 622
		f 3 -1470 1875 -1465
		mu 0 3 630 633 629
		f 3 -1456 1876 1877
		mu 0 3 625 626 773
		f 3 -1878 1878 1879
		mu 0 3 625 773 565
		f 3 -1454 1880 1881
		mu 0 3 623 625 568
		f 3 -1452 -1874 -1460
		mu 0 3 624 622 628
		f 3 -1451 1882 1883
		mu 0 3 621 623 570
		f 3 -1832 -1875 -1448
		mu 0 3 620 631 622
		f 3 -1446 1884 1885
		mu 0 3 619 621 572
		f 3 -1444 -1834 -1833
		mu 0 3 620 618 768
		f 3 -1443 1886 1887
		mu 0 3 617 619 574
		f 3 -1853 -1835 -1440
		mu 0 3 616 766 618
		f 3 -1438 1888 1889
		mu 0 3 615 617 576
		f 3 -1855 -1854 -1436
		mu 0 3 614 764 616;
	setAttr ".fc[1000:1499]"
		f 3 -1434 1890 1891
		mu 0 3 613 615 578
		f 3 -1432 -1860 -1856
		mu 0 3 614 612 762
		f 3 -1431 1892 1893
		mu 0 3 611 613 580
		f 3 -1863 -1861 -1428
		mu 0 3 610 760 612
		f 3 -1426 1894 1895
		mu 0 3 609 611 582
		f 3 -1424 1896 -1864
		mu 0 3 610 608 758
		f 3 -1807 -1897 -1418
		mu 0 3 607 758 608
		f 3 -1416 1897 -1805
		mu 0 3 607 605 659
		f 3 -1525 -1898 -1410
		mu 0 3 604 659 605
		f 3 -1408 -1534 -1527
		mu 0 3 604 602 660
		f 3 -1406 1898 1899
		mu 0 3 601 603 590
		f 3 -1800 -1535 -1404
		mu 0 3 600 663 602
		f 3 -1402 1900 1901
		mu 0 3 599 601 592
		f 3 -1798 -1801 -1400
		mu 0 3 598 665 600
		f 3 -1396 -1546 -1799
		mu 0 3 598 597 667
		f 3 -1556 -1549 -1394
		mu 0 3 1 669 597
		f 3 -1399 1902 -1391
		mu 0 3 596 599 594
		f 3 -1903 -1902 -1384
		mu 0 3 594 599 592
		f 3 -1382 1903 1904
		mu 0 3 593 591 532
		f 3 1905 1906 -1905
		mu 0 3 532 14 593
		f 3 -1900 -1380 -1901
		mu 0 3 601 590 592
		f 3 -1899 -1413 -1374
		mu 0 3 590 603 589
		f 3 -1414 1907 -1373
		mu 0 3 589 606 587
		f 3 -1908 -1421 -1366
		mu 0 3 587 606 586
		f 3 -1422 1908 -1365
		mu 0 3 586 609 584
		f 3 -1909 -1896 -1358
		mu 0 3 584 609 582
		f 3 -1352 -1895 -1894
		mu 0 3 580 582 611
		f 3 -1350 1909 1910
		mu 0 3 581 579 544
		f 3 -1893 -1892 -1348
		mu 0 3 580 613 578
		f 3 -1342 -1891 -1890
		mu 0 3 576 578 615
		f 3 -1336 -1889 -1888
		mu 0 3 574 576 617
		f 3 -1334 1911 1912
		mu 0 3 575 573 550
		f 3 -1887 -1886 -1332
		mu 0 3 574 619 572
		f 3 -1326 -1885 -1884
		mu 0 3 570 572 621
		f 3 -1324 1913 1914
		mu 0 3 571 569 554
		f 3 -1883 -1882 -1322
		mu 0 3 570 623 568
		f 3 -1316 -1881 1915
		mu 0 3 566 568 625
		f 3 -1314 1916 1917
		mu 0 3 567 564 558
		f 3 -1880 -1313 -1916
		mu 0 3 625 565 566
		f 3 -1304 1918 1919
		mu 0 3 561 562 774
		f 3 1920 1921 -1920
		mu 0 3 774 775 561
		f 3 1922 1923 -1922
		mu 0 3 775 776 561
		f 3 -1923 1924 1925
		mu 0 3 776 775 777
		f 3 1926 -1926 1927
		mu 0 3 778 776 777
		f 3 -1928 1928 1929
		mu 0 3 778 777 779
		f 3 1930 1931 -1930
		mu 0 3 779 780 778
		f 3 1932 -1932 1933
		mu 0 3 781 778 780
		f 3 1934 -1934 1935
		mu 0 3 371 781 780
		f 3 -1936 1936 1937
		mu 0 3 371 780 366
		f 3 -1933 1938 1939
		mu 0 3 778 781 782
		f 3 1940 -1939 1941
		mu 0 3 783 782 781
		f 3 1942 -1942 1943
		mu 0 3 372 783 781
		f 3 1944 -1943 1945
		mu 0 3 784 783 372
		f 3 1946 1947 -1945
		mu 0 3 784 555 783
		f 3 -1941 1948 1949
		mu 0 3 782 783 557
		f 3 -1931 1950 1951
		mu 0 3 780 779 364
		f 3 -1929 1952 1953
		mu 0 3 779 777 785
		f 3 1954 1955 -1953
		mu 0 3 777 786 785
		f 3 1956 1957 -1956
		mu 0 3 786 787 785
		f 3 -1958 1958 1959
		mu 0 3 785 787 361
		f 3 -1959 1960 1961
		mu 0 3 361 787 788
		f 3 1962 -1961 1963
		mu 0 3 789 788 787
		f 3 -1963 1964 1965
		mu 0 3 788 789 790
		f 3 1966 -1965 1967
		mu 0 3 791 790 789
		f 3 -1967 1968 1969
		mu 0 3 790 791 792
		f 3 1970 1971 -1970
		mu 0 3 792 793 790
		f 3 -1971 1972 1973
		mu 0 3 793 792 794
		f 3 -1974 1974 1975
		mu 0 3 793 794 795
		f 3 -1976 1976 1977
		mu 0 3 793 795 355
		f 3 1978 -1966 -1972
		mu 0 3 793 788 790
		f 3 -1979 1979 1980
		mu 0 3 788 793 357
		f 3 1981 -1964 -1957
		mu 0 3 786 789 787
		f 3 1982 1983 -1982
		mu 0 3 786 796 789
		f 3 1984 -1983 1985
		mu 0 3 775 796 786
		f 3 1986 1987 -1985
		mu 0 3 775 797 796
		f 3 -1954 1988 1989
		mu 0 3 779 785 362
		f 3 1990 -1927 -1940
		mu 0 3 782 776 778
		f 3 1991 1992 -1991
		mu 0 3 782 559 776
		f 3 -1955 -1925 -1986
		mu 0 3 786 777 775
		f 3 -1921 1993 -1987
		mu 0 3 775 774 797
		f 3 -1302 -1924 -1993
		mu 0 3 559 561 776
		f 3 -1300 -1917 -1308
		mu 0 3 560 558 564
		f 3 -1299 -1992 -1950
		mu 0 3 557 559 782
		f 3 -1320 -1918 -1296
		mu 0 3 556 567 558
		f 3 -1294 -1949 -1948
		mu 0 3 555 557 783
		f 3 -1292 -1914 -1321
		mu 0 3 556 554 569
		f 3 -1291 -1947 1994
		mu 0 3 553 555 784
		f 3 1995 1996 -1995
		mu 0 3 784 798 553
		f 3 -1996 1997 1998
		mu 0 3 798 784 373
		f 3 -1330 -1915 -1288
		mu 0 3 552 571 554
		f 3 -1286 -1997 1999
		mu 0 3 551 553 798
		f 3 2000 -2000 2001
		mu 0 3 799 551 798
		f 3 -2002 2002 2003
		mu 0 3 799 798 375
		f 3 -1284 -1912 -1331
		mu 0 3 552 550 573
		f 3 -1283 -2001 2004
		mu 0 3 549 551 799
		f 3 2005 2006 -2005
		mu 0 3 799 800 549
		f 3 -2006 2007 2008
		mu 0 3 800 799 377
		f 3 2009 -2009 2010
		mu 0 3 801 800 377
		f 3 2011 -2010 2012
		mu 0 3 802 800 801
		f 3 2013 2014 -2013
		mu 0 3 801 803 802
		f 3 2015 -2015 2016
		mu 0 3 804 802 803
		f 3 2017 2018 -2017
		mu 0 3 803 805 804
		f 3 2019 -2019 2020
		mu 0 3 806 804 805
		f 3 -2021 2021 2022
		mu 0 3 806 805 807
		f 3 -2022 2023 2024
		mu 0 3 807 805 515
		f 3 2025 -2023 2026
		mu 0 3 808 806 807
		f 3 2027 2028 -2027
		mu 0 3 807 520 808
		f 3 2029 -2026 2030
		mu 0 3 541 806 808
		f 3 -2020 2031 2032
		mu 0 3 804 806 543
		f 3 -2018 2033 2034
		mu 0 3 805 803 514
		f 3 2035 -2034 2036
		mu 0 3 381 514 803
		f 3 2037 2038 -2016
		mu 0 3 804 545 802
		f 3 -2014 2039 -2037
		mu 0 3 803 801 381
		f 3 2040 2041 -2012
		mu 0 3 802 547 800
		f 3 -1340 -1913 -1280
		mu 0 3 548 575 550
		f 3 -1278 -2007 -2042
		mu 0 3 547 549 800
		f 3 -1276 -1346 -1341
		mu 0 3 548 546 577
		f 3 -1274 -2041 -2039
		mu 0 3 545 547 802
		f 3 -1272 -1910 -1347
		mu 0 3 546 544 579
		f 3 -1271 -2038 -2033
		mu 0 3 543 545 804
		f 3 -1356 -1911 -1268
		mu 0 3 542 581 544
		f 3 -1266 -2032 -2030
		mu 0 3 541 543 806
		f 3 -1264 2042 -1357
		mu 0 3 542 539 583
		f 3 -1262 -2031 2043
		mu 0 3 540 541 808
		f 3 2044 2045 -2044
		mu 0 3 808 522 540
		f 3 -1361 -2043 -1256
		mu 0 3 538 583 539
		f 3 -1254 2046 -1363
		mu 0 3 538 536 585
		f 3 -1369 -2047 -1248
		mu 0 3 535 585 536
		f 3 -1246 -1378 -1371
		mu 0 3 535 533 588
		f 3 -1904 -1379 -1242
		mu 0 3 532 591 533
		f 3 -1906 -1240 2047
		mu 0 3 14 532 530
		f 3 -1244 2048 -1231
		mu 0 3 529 534 527
		f 3 -2049 -1251 -1224
		mu 0 3 527 534 526
		f 3 -1252 -1260 -1223
		mu 0 3 526 537 524
		f 3 -1261 -2046 -1216
		mu 0 3 524 540 522
		f 3 -2045 -2029 -1210
		mu 0 3 522 808 520
		f 3 -2028 2049 -1204
		mu 0 3 520 807 517
		f 3 -1192 -2050 -2025
		mu 0 3 515 517 807
		f 3 -2035 -1188 -2024
		mu 0 3 805 514 515
		f 3 -1190 -1182 -1198
		mu 0 3 516 513 511
		f 3 2050 -1171 2051
		mu 0 3 463 507 509
		f 3 -1176 -1168 2052
		mu 0 3 511 508 506
		f 3 2053 -1167 2054
		mu 0 3 465 505 507
		f 3 -2054 2055 2056
		mu 0 3 505 465 469
		f 3 -1199 -2053 -1164
		mu 0 3 504 511 506
		f 3 2057 -1163 -2057
		mu 0 3 469 503 505
		f 3 -1160 2058 -1197
		mu 0 3 504 501 518
		f 3 2059 2060 -1153
		mu 0 3 502 477 500
		f 3 -1202 -2059 -1150
		mu 0 3 499 518 501
		f 3 2061 2062 -1149
		mu 0 3 500 479 498
		f 3 -1208 -1203 -1146
		mu 0 3 497 519 499
		f 3 2063 2064 -1145
		mu 0 3 498 481 496
		f 3 -1214 -1209 -1142
		mu 0 3 495 521 497
		f 3 2065 2066 -1141
		mu 0 3 496 483 494
		f 3 -1220 -1215 -1138
		mu 0 3 493 523 495
		f 3 2067 2068 -1137
		mu 0 3 494 485 491
		f 3 -1227 -1221 -1134
		mu 0 3 492 525 493
		f 3 -1132 -1236 -1229
		mu 0 3 492 490 528
		f 3 2069 -1237 -1128
		mu 0 3 489 531 490
		f 3 2070 -2070 2071
		mu 0 3 17 531 489
		f 3 -1130 -2069 -1116
		mu 0 3 487 491 485
		f 3 -2068 -2067 -1110
		mu 0 3 485 494 483
		f 3 -2066 -2065 -1104
		mu 0 3 483 496 481
		f 3 -2064 -2063 -1098
		mu 0 3 481 498 479
		f 3 -2062 -2061 -1092
		mu 0 3 479 500 477
		f 3 -2060 -1159 -1086
		mu 0 3 477 502 475
		f 3 -1158 -1068 -1080
		mu 0 3 475 470 471
		f 3 -2058 -1066 -1156
		mu 0 3 503 469 470
		f 3 -1062 2072 -1072
		mu 0 3 468 467 473
		f 3 2073 2074 -2073
		mu 0 3 467 44 473
		f 3 -2056 -1056 -1065
		mu 0 3 469 465 466
		f 3 -2051 -1054 -2055
		mu 0 3 507 463 465
		f 3 2075 -1048 -2052
		mu 0 3 509 459 463
		f 3 -2076 2076 -1036
		mu 0 3 459 509 457
		f 3 -1173 -1030 -2077
		mu 0 3 509 456 457
		f 3 -1174 -1181 -1028
		mu 0 3 456 510 454
		f 3 2077 -1023 -1180
		mu 0 3 512 453 454
		f 3 2078 2079 -2078
		mu 0 3 512 383 453
		f 3 2080 2081 -1021
		mu 0 3 453 385 452
		f 3 -1015 2082 -1026
		mu 0 3 451 436 455
		f 3 -2083 -960 -1031
		mu 0 3 455 436 435
		f 3 -958 2083 -1034
		mu 0 3 435 432 458
		f 3 -956 -965 -1004
		mu 0 3 433 434 438
		f 3 -2084 -952 -1039
		mu 0 3 458 432 431
		f 3 -950 2084 -1042
		mu 0 3 431 430 461
		f 3 2085 -2085 2086
		mu 0 3 58 461 430
		f 3 -1005 -944 -955
		mu 0 3 433 427 429
		f 3 -1001 -938 -1006
		mu 0 3 441 425 427
		f 3 -998 -932 -1002
		mu 0 3 442 423 425
		f 3 -992 -926 -999
		mu 0 3 444 421 423
		f 3 -988 -920 -993
		mu 0 3 446 419 421
		f 3 2087 -914 -989
		mu 0 3 448 417 419
		f 3 -2088 2088 2089
		mu 0 3 417 448 405
		f 3 2090 -908 -2090
		mu 0 3 405 415 417
		f 3 2091 -902 2092
		mu 0 3 406 412 415
		f 3 2093 -878 2094
		mu 0 3 809 409 407
		f 3 2095 2096 -2095
		mu 0 3 407 810 809
		f 3 2097 -2097 2098
		mu 0 3 811 809 810
		f 3 2099 2100 -2099
		mu 0 3 810 812 811
		f 3 2101 -2101 2102
		mu 0 3 282 811 812
		f 3 -2102 2103 2104
		mu 0 3 811 282 98
		f 3 -2100 2105 2106
		mu 0 3 812 810 402
		f 3 -2098 2107 2108
		mu 0 3 809 811 96
		f 3 -2094 2109 2110
		mu 0 3 409 809 94
		f 3 -2092 -877 -891
		mu 0 3 412 406 408
		f 3 -2096 -874 2111
		mu 0 3 810 407 404
		f 3 -2091 -873 -2093
		mu 0 3 415 405 406
		f 3 -986 -871 -2089
		mu 0 3 448 403 405
		f 3 -868 -2106 -2112
		mu 0 3 404 402 810
		f 3 -866 -987 2112
		mu 0 3 400 403 447
		f 3 -864 2113 -2107
		mu 0 3 402 401 812
		f 3 2114 -2114 2115
		mu 0 3 283 812 401
		f 3 2116 -862 2117
		mu 0 3 285 401 399
		f 3 2118 2119 -2118
		mu 0 3 399 813 285
		f 3 -990 -861 -2113
		mu 0 3 447 398 400
		f 3 -2119 -858 2120
		mu 0 3 813 399 396
		f 3 -994 -857 -991
		mu 0 3 445 397 398
		f 3 -854 -997 2121
		mu 0 3 394 397 449
		f 3 2122 -2121 -852
		mu 0 3 395 813 396
		f 3 2123 -2123 2124
		mu 0 3 325 813 395
		f 3 -2124 2125 2126
		mu 0 3 813 325 286
		f 3 2127 -850 2128
		mu 0 3 326 395 393
		f 3 -1008 -849 -2122
		mu 0 3 449 392 394
		f 3 2129 -846 2130
		mu 0 3 328 393 390
		f 3 -1010 -845 -1009
		mu 0 3 439 391 392
		f 3 -1020 -843 -1013
		mu 0 3 450 389 391
		f 3 -840 2131 -2131
		mu 0 3 390 388 328
		f 3 -838 -1019 -2082
		mu 0 3 385 389 452
		f 3 -821 -2081 -2080
		mu 0 3 383 385 453
		f 3 -817 -2079 -1185
		mu 0 3 382 383 512
		f 3 -2036 -814 -1186
		mu 0 3 514 381 382
		f 3 -812 -2040 2132
		mu 0 3 378 381 801
		f 3 -810 -826 -818
		mu 0 3 380 379 384
		f 3 -808 2133 -828
		mu 0 3 379 376 387
		f 3 -2011 -806 -2133
		mu 0 3 801 377 378
		f 3 -804 -2008 -2004
		mu 0 3 375 377 799
		f 3 -802 -834 -2134
		mu 0 3 376 374 387
		f 3 -2003 -1999 -800
		mu 0 3 375 798 373
		f 3 -796 -1998 -1946
		mu 0 3 372 373 784
		f 3 -1944 -1935 -795
		mu 0 3 372 781 371
		f 3 -799 -790 -835
		mu 0 3 374 370 369
		f 3 -784 -793 -1938
		mu 0 3 366 368 371
		f 3 -782 2134 2135
		mu 0 3 367 365 336
		f 3 -1937 -1952 -780
		mu 0 3 366 780 364
		f 3 -778 2136 2137
		mu 0 3 365 363 338
		f 3 -1990 -776 -1951
		mu 0 3 779 362 364
		f 3 -770 -1989 -1960
		mu 0 3 361 362 785
		f 3 -1962 2138 -768
		mu 0 3 361 788 359
		f 3 -762 -2139 -1981
		mu 0 3 357 359 788
		f 3 -760 2139 2140
		mu 0 3 358 356 345
		f 3 -1980 -1978 -758
		mu 0 3 357 793 355
		f 3 -756 2141 2142
		mu 0 3 356 353 347
		f 3 -1977 2143 -755
		mu 0 3 355 795 354
		f 3 -746 2144 2145
		mu 0 3 350 351 814
		f 3 2146 2147 -2146
		mu 0 3 814 815 350
		f 3 2148 2149 -2148
		mu 0 3 815 816 350
		f 3 -2149 2150 2151
		mu 0 3 816 815 262
		f 3 2152 -2152 2153
		mu 0 3 307 816 262
		f 3 -2147 2154 2155
		mu 0 3 815 814 817
		f 3 2156 2157 -2156
		mu 0 3 817 260 815
		f 3 -744 -2150 2158
		mu 0 3 348 350 816
		f 3 2159 2160 -2159
		mu 0 3 816 308 348
		f 3 -742 -2142 -750
		mu 0 3 349 347 353
		f 3 -740 -2161 2161
		mu 0 3 346 348 308
		f 3 -2140 -2143 -738
		mu 0 3 345 356 347
		f 3 -736 2162 2163
		mu 0 3 344 346 309
		f 3 -734 2164 -2141
		mu 0 3 345 343 358
		f 3 -765 -2165 -728
		mu 0 3 342 358 343
		f 3 -726 -774 -767
		mu 0 3 342 340 360
		f 3 -725 2165 2166
		mu 0 3 339 341 314
		f 3 -775 -722 -2137
		mu 0 3 363 340 338
		f 3 -720 2167 2168
		mu 0 3 337 339 316
		f 3 -2135 -2138 -718
		mu 0 3 336 365 338
		f 3 -712 2169 -2136
		mu 0 3 336 334 367
		f 3 -787 -2170 -706
		mu 0 3 333 367 334
		f 3 -704 -833 -789
		mu 0 3 333 332 369
		f 3 -831 -702 2170
		mu 0 3 386 332 330
		f 3 -696 -825 -2171
		mu 0 3 330 329 386
		f 3 -694 -2132 -836
		mu 0 3 329 328 388
		f 3 -2130 -692 -2129
		mu 0 3 393 328 326
		f 3 -2128 -688 -2125
		mu 0 3 395 326 325
		f 3 -699 -682 -691
		mu 0 3 327 323 324
		f 3 -680 -701 -709
		mu 0 3 322 323 331
		f 3 -711 2171 -678
		mu 0 3 322 335 320
		f 3 -672 -2172 -717
		mu 0 3 318 320 335
		f 3 -670 2172 2173
		mu 0 3 319 317 293
		f 3 -716 -2169 -668
		mu 0 3 318 337 316
		f 3 -666 2174 2175
		mu 0 3 317 315 295
		f 3 -2167 -664 -2168
		mu 0 3 339 314 316
		f 3 -658 -2166 -731
		mu 0 3 313 314 341
		f 3 -733 2176 -656
		mu 0 3 313 344 311
		f 3 -650 -2177 -2164
		mu 0 3 309 311 344
		f 3 -2163 -2162 -646
		mu 0 3 309 346 308
		f 3 -2160 -2153 -645
		mu 0 3 308 816 307
		f 3 -648 -638 2177
		mu 0 3 310 306 304
		f 3 -632 2178 -2178
		mu 0 3 304 300 310
		f 3 -631 2179 2180
		mu 0 3 301 303 271
		f 3 -653 -2179 -622
		mu 0 3 299 310 300
		f 3 -620 -662 -655
		mu 0 3 299 297 312
		f 3 -619 -627 2181
		mu 0 3 296 298 302
		f 3 -2182 2182 2183
		mu 0 3 296 302 277
		f 3 -663 -616 -2175
		mu 0 3 315 297 295
		f 3 -614 -2184 2184
		mu 0 3 294 296 277
		f 3 -2173 -2176 -612
		mu 0 3 293 317 295
		f 3 -606 2185 -2174
		mu 0 3 293 290 319
		f 3 -605 2186 2187
		mu 0 3 291 292 280
		f 3 2188 2189 -2188
		mu 0 3 280 284 291
		f 3 -675 -2186 -600
		mu 0 3 289 319 290
		f 3 -598 -684 -677
		mu 0 3 289 288 321
		f 3 -596 -2126 -687
		mu 0 3 288 286 325
		f 3 -594 -603 -2190
		mu 0 3 284 287 291
		f 3 -592 -2120 -2127
		mu 0 3 286 285 813
		f 3 -2117 -590 -2116
		mu 0 3 401 285 283
		f 3 -2115 -586 -2103
		mu 0 3 812 283 282
		f 3 -2189 -580 -589
		mu 0 3 284 280 281
		f 3 -578 -2187 -611
		mu 0 3 278 280 292
		f 3 -576 2190 2191
		mu 0 3 279 276 101
		f 3 -610 -2185 -574
		mu 0 3 278 294 277
		f 3 -2183 2192 -573
		mu 0 3 277 302 275
		f 3 -568 2193 2194
		mu 0 3 103 274 151
		f 3 -2193 -629 -566
		mu 0 3 275 302 273
		f 3 -564 2195 2196
		mu 0 3 274 272 152
		f 3 -2181 -562 -628
		mu 0 3 301 271 273
		f 3 -556 -2180 2197
		mu 0 3 268 271 303
		f 3 -554 2198 2199
		mu 0 3 270 269 156
		f 3 -2199 2200 2201
		mu 0 3 156 269 818
		f 3 2202 2203 -2201
		mu 0 3 269 248 818
		f 3 -2203 -552 2204
		mu 0 3 248 269 266
		f 3 -635 -550 -2198
		mu 0 3 303 267 268
		f 3 -548 -637 2205
		mu 0 3 265 267 305
		f 3 -643 -542 -2206
		mu 0 3 305 263 265
		f 3 -540 2206 2207
		mu 0 3 264 261 253
		f 3 -538 -642 -2154
		mu 0 3 262 263 307
		f 3 -536 -2151 -2158
		mu 0 3 260 262 815
		f 3 -534 2208 -2207
		mu 0 3 261 258 253
		f 3 -2157 2209 -533
		mu 0 3 260 817 259
		f 3 -524 2210 2211
		mu 0 3 255 256 819
		f 3 2212 2213 -2212
		mu 0 3 819 820 255
		f 3 2214 2215 -2214
		mu 0 3 820 821 255
		f 3 -2215 2216 2217
		mu 0 3 821 820 822
		f 3 2218 -2218 2219
		mu 0 3 823 821 822
		f 3 2220 2221 -2220
		mu 0 3 822 239 823
		f 3 -2219 2222 2223
		mu 0 3 821 823 251
		f 3 2224 2225 -2223
		mu 0 3 823 246 251
		f 3 -2225 2226 2227
		mu 0 3 246 823 241
		f 3 2228 -2217 2229
		mu 0 3 236 822 820
		f 3 2230 -2230 2231
		mu 0 3 824 236 820
		f 3 -2213 2232 -2232
		mu 0 3 820 819 824
		f 3 -522 -2216 2233
		mu 0 3 252 255 821
		f 3 -520 -2209 -528
		mu 0 3 254 253 258
		f 3 -518 2234 -2208
		mu 0 3 253 250 264
		f 3 -516 -2234 -2224
		mu 0 3 251 252 821
		f 3 -512 -544 -2235
		mu 0 3 250 249 264
		f 3 -546 -510 -2205
		mu 0 3 266 249 248
		f 3 -508 2235 -2204
		mu 0 3 248 245 818
		f 3 -515 -2226 -507
		mu 0 3 247 251 246
		f 3 -2236 -502 2236
		mu 0 3 818 245 244
		f 3 2237 2238 -2237
		mu 0 3 244 157 818
		f 3 -2228 -496 -505
		mu 0 3 246 241 243
		f 3 -490 -2227 -2222
		mu 0 3 239 241 823
		f 3 -488 2239 2240
		mu 0 3 240 238 168
		f 3 -2240 2241 2242
		mu 0 3 168 238 226
		f 3 -2221 2243 -486
		mu 0 3 239 822 237
		f 3 -2229 -480 -2244
		mu 0 3 822 236 237
		f 3 -2231 2244 -478
		mu 0 3 236 824 235
		f 3 -460 -482 -475
		mu 0 3 229 228 234
		f 3 -484 -458 -2242
		mu 0 3 238 228 226
		f 3 -446 -457 -465
		mu 0 3 222 224 227
		f 3 -444 2245 2246
		mu 0 3 223 221 180
		f 3 -464 -471 -442
		mu 0 3 222 230 220
		f 3 2247 -2246 -440
		mu 0 3 219 180 221
		f 3 -2248 2248 2249
		mu 0 3 180 219 825
		f 3 2250 -439 -470
		mu 0 3 232 218 220
		f 3 -2251 2251 2252
		mu 0 3 218 232 826
		f 3 2253 -2249 -436
		mu 0 3 217 825 219
		f 3 2254 -2254 2255
		mu 0 3 827 825 217
		f 3 2256 2257 -2256
		mu 0 3 217 828 827
		f 3 2258 2259 -2258
		mu 0 3 828 829 827
		f 3 2260 -2260 2261
		mu 0 3 181 827 829
		f 3 -2259 2262 2263
		mu 0 3 829 828 203
		f 3 2264 2265 -2263
		mu 0 3 828 208 203
		f 3 -2261 2266 -2255
		mu 0 3 827 181 825
		f 3 2267 -434 -2253
		mu 0 3 826 216 218
		f 3 -2268 2268 2269
		mu 0 3 216 826 830
		f 3 -2257 -432 2270
		mu 0 3 828 217 214
		f 3 2271 -430 -2270
		mu 0 3 830 215 216
		f 3 -2272 2272 2273
		mu 0 3 215 830 831
		f 3 2274 2275 -2274
		mu 0 3 831 832 215
		f 3 -2275 2276 2277
		mu 0 3 832 831 833
		f 3 2278 -2278 2279
		mu 0 3 834 832 833
		f 3 2280 -2279 2281
		mu 0 3 835 832 834
		f 3 2282 2283 -2281
		mu 0 3 835 213 832
		f 3 -2276 -2284 -429
		mu 0 3 215 832 213
		f 3 -426 2284 -2271
		mu 0 3 214 211 828
		f 3 -2283 2285 -425
		mu 0 3 213 835 212
		f 3 -2265 -2285 -420
		mu 0 3 208 828 211
		f 3 -406 -2266 -415
		mu 0 3 204 203 208
		f 3 -404 2286 -2264
		mu 0 3 203 200 829
		f 3 2287 -2287 2288
		mu 0 3 183 829 200
		f 3 -408 2289 -403
		mu 0 3 202 205 201
		f 3 -2289 -398 2290
		mu 0 3 183 200 198
		f 3 -394 2291 2292
		mu 0 3 198 195 184
		f 3 -390 2293 2294
		mu 0 3 194 196 836
		f 3 2295 2296 -2295
		mu 0 3 836 837 194
		f 3 -2296 2297 2298
		mu 0 3 837 836 838
		f 3 2299 2300 -2299
		mu 0 3 838 839 837
		f 3 -2301 2301 2302
		mu 0 3 837 839 840
		f 3 -2303 2303 2304
		mu 0 3 837 840 193
		f 3 2305 -2304 2306
		mu 0 3 841 193 840
		f 3 -2307 2307 2308
		mu 0 3 841 840 842
		f 3 -2308 2309 2310
		mu 0 3 842 840 843
		f 3 -2311 2311 2312
		mu 0 3 842 843 844
		f 3 2313 -2312 2314
		mu 0 3 845 844 843
		f 3 2315 -2315 2316
		mu 0 3 839 845 843
		f 3 2317 -2316 2318
		mu 0 3 846 845 839
		f 3 -2319 2319 2320
		mu 0 3 846 839 847
		f 3 2321 2322 -2318
		mu 0 3 846 848 845
		f 3 -2322 2323 2324
		mu 0 3 848 846 849
		f 3 2325 2326 -2325
		mu 0 3 849 850 848
		f 3 2327 2328 -2327
		mu 0 3 850 851 848
		f 3 2329 -2329 2330
		mu 0 3 852 848 851
		f 3 2331 -2331 2332
		mu 0 3 853 852 851
		f 3 2333 -2333 2334
		mu 0 3 854 853 851
		f 3 2335 -2334 2336
		mu 0 3 855 853 854
		f 3 -2336 2337 2338
		mu 0 3 853 855 856
		f 3 2339 -2338 2340
		mu 0 3 857 856 855
		f 3 -2340 2341 2342
		mu 0 3 856 857 858
		f 3 2343 2344 -2343
		mu 0 3 858 859 856
		f 3 2345 -2345 2346
		mu 0 3 860 856 859
		f 3 2347 -2347 2348
		mu 0 3 861 860 859
		f 3 2349 -2349 2350
		mu 0 3 862 861 859
		f 3 2351 -2351 2352
		mu 0 3 863 862 859
		f 3 -2352 2353 2354
		mu 0 3 862 863 864
		f 3 2355 2356 -2355
		mu 0 3 864 865 862
		f 3 2357 -2357 2358
		mu 0 3 866 862 865
		f 3 2359 2360 -2359
		mu 0 3 865 867 866
		f 3 2361 -2361 2362
		mu 0 3 868 866 867
		f 3 2363 2364 -2363
		mu 0 3 867 869 868
		f 3 2365 -2365 2366
		mu 0 3 870 868 869
		f 3 2367 2368 -2367
		mu 0 3 869 871 870
		f 3 2369 -2369 2370
		mu 0 3 872 870 871
		f 3 2371 2372 -2371
		mu 0 3 871 873 872
		f 3 2373 -2373 2374
		mu 0 3 874 872 873
		f 3 2375 2376 -2375
		mu 0 3 873 875 874
		f 3 2377 2378 -2377
		mu 0 3 875 876 874
		f 3 2379 -2379 2380
		mu 0 3 877 874 876
		f 3 2381 2382 -2381
		mu 0 3 876 878 877
		f 3 -2383 2383 2384
		mu 0 3 877 878 879
		f 3 -2385 2385 2386
		mu 0 3 877 879 880
		f 3 2387 -2386 2388
		mu 0 3 881 880 879
		f 3 2389 2390 -2389
		mu 0 3 879 174 881
		f 3 -2391 2391 2392
		mu 0 3 881 174 882
		f 3 -2393 2393 2394
		mu 0 3 881 882 189
		f 3 -2395 2395 2396
		mu 0 3 881 189 883
		f 3 -2388 -2397 2397
		mu 0 3 880 881 883
		f 3 2398 -2398 2399
		mu 0 3 884 880 883
		f 3 -2400 2400 2401
		mu 0 3 884 883 885
		f 3 2402 -2401 2403
		mu 0 3 190 885 883
		f 3 -2403 2404 2405
		mu 0 3 885 190 886
		f 3 2406 -2406 2407
		mu 0 3 887 885 886
		f 3 2408 -2408 2409
		mu 0 3 841 887 886
		f 3 -2407 2410 2411
		mu 0 3 885 887 888
		f 3 2412 -2411 2413
		mu 0 3 889 888 887
		f 3 -2414 2414 2415
		mu 0 3 889 887 842
		f 3 -2416 2416 2417
		mu 0 3 889 842 890
		f 3 2418 -2418 2419
		mu 0 3 891 889 890
		f 3 2420 2421 -2420
		mu 0 3 890 852 891
		f 3 2422 -2422 2423
		mu 0 3 860 891 852
		f 3 -2421 2424 2425
		mu 0 3 852 890 844
		f 3 -2419 2426 2427
		mu 0 3 889 891 892
		f 3 -2427 2428 2429
		mu 0 3 892 891 861
		f 3 2430 -2430 2431
		mu 0 3 866 892 861
		f 3 2432 -2428 2433
		mu 0 3 893 889 892
		f 3 2434 -2434 2435
		mu 0 3 868 893 892
		f 3 -2413 -2433 2436
		mu 0 3 888 889 893
		f 3 2437 -2437 2438
		mu 0 3 894 888 893
		f 3 2439 -2439 2440
		mu 0 3 870 894 893
		f 3 2441 -2438 2442
		mu 0 3 884 888 894
		f 3 2443 -2443 2444
		mu 0 3 895 884 894
		f 3 2445 -2445 2446
		mu 0 3 872 895 894
		f 3 2447 -2410 -2405
		mu 0 3 190 841 886
		f 3 -2442 -2402 -2412
		mu 0 3 888 884 885
		f 3 2448 -2399 -2444
		mu 0 3 895 880 884
		f 3 -2387 -2449 2449
		mu 0 3 877 880 895
		f 3 2450 2451 -2384
		mu 0 3 878 173 879
		f 3 -2451 2452 2453
		mu 0 3 173 878 896
		f 3 2454 -2453 2455
		mu 0 3 897 896 878
		f 3 2456 2457 -2455
		mu 0 3 897 164 896
		f 3 2458 -2457 2459
		mu 0 3 898 164 897
		f 3 2460 2461 -2460
		mu 0 3 897 899 898
		f 3 2462 -2462 2463
		mu 0 3 900 898 899
		f 3 2464 -2464 2465
		mu 0 3 875 900 899
		f 3 -2465 2466 2467
		mu 0 3 900 875 901
		f 3 2468 -2468 2469
		mu 0 3 902 900 901
		f 3 2470 -2470 2471
		mu 0 3 903 902 901
		f 3 -2472 2472 2473
		mu 0 3 903 901 904
		f 3 2474 -2474 2475
		mu 0 3 905 903 904
		f 3 2476 2477 -2476
		mu 0 3 904 906 905
		f 3 2478 -2478 2479
		mu 0 3 907 905 906
		f 3 2480 2481 -2480
		mu 0 3 906 908 907;
	setAttr ".fc[1500:1999]"
		f 3 2482 -2482 2483
		mu 0 3 909 907 908
		f 3 2484 2485 -2484
		mu 0 3 908 910 909
		f 3 2486 -2486 2487
		mu 0 3 911 909 910
		f 3 2488 2489 -2488
		mu 0 3 910 912 911
		f 3 2490 -2490 2491
		mu 0 3 913 911 912
		f 3 2492 2493 -2492
		mu 0 3 912 914 913
		f 3 2494 -2494 2495
		mu 0 3 915 913 914
		f 3 2496 2497 -2496
		mu 0 3 914 916 915
		f 3 2498 -2498 2499
		mu 0 3 917 915 916
		f 3 2500 2501 -2500
		mu 0 3 916 918 917
		f 3 2502 -2502 2503
		mu 0 3 919 917 918
		f 3 2504 2505 -2504
		mu 0 3 918 920 919
		f 3 2506 2507 -2506
		mu 0 3 920 921 919
		f 3 -2508 2508 2509
		mu 0 3 919 921 922
		f 3 -2510 2510 2511
		mu 0 3 919 922 923
		f 3 -2511 2512 2513
		mu 0 3 923 922 131
		f 3 2514 -2513 2515
		mu 0 3 924 131 922
		f 3 2516 2517 -2516
		mu 0 3 922 925 924
		f 3 2518 -2518 2519
		mu 0 3 926 924 925
		f 3 2520 2521 -2520
		mu 0 3 925 927 926
		f 3 -2521 2522 2523
		mu 0 3 927 925 928
		f 3 -2523 2524 2525
		mu 0 3 928 925 929
		f 3 -2525 2526 2527
		mu 0 3 929 925 921
		f 3 2528 2529 -2528
		mu 0 3 921 930 929
		f 3 2530 -2530 2531
		mu 0 3 931 929 930
		f 3 2532 2533 -2532
		mu 0 3 930 932 931
		f 3 2534 -2534 2535
		mu 0 3 933 931 932
		f 3 2536 2537 -2536
		mu 0 3 932 934 933
		f 3 2538 2539 -2538
		mu 0 3 934 935 933
		f 3 2540 2541 -2540
		mu 0 3 935 936 933
		f 3 2542 2543 -2542
		mu 0 3 936 937 933
		f 3 2544 2545 -2543
		mu 0 3 936 938 937
		f 3 2546 -2546 2547
		mu 0 3 939 937 938
		f 3 2548 2549 -2548
		mu 0 3 938 940 939
		f 3 2550 2551 -2550
		mu 0 3 940 928 939
		f 3 2552 -2551 2553
		mu 0 3 941 928 940
		f 3 2554 2555 -2554
		mu 0 3 940 942 941
		f 3 2556 -2555 2557
		mu 0 3 943 942 940
		f 3 2558 2559 -2557
		mu 0 3 943 944 942
		f 3 2560 2561 -2559
		mu 0 3 943 945 944
		f 3 -2561 2562 2563
		mu 0 3 945 943 946
		f 3 2564 2565 -2563
		mu 0 3 943 947 946
		f 3 2566 2567 -2566
		mu 0 3 947 948 946
		f 3 2568 -2568 2569
		mu 0 3 949 946 948
		f 3 2570 2571 -2570
		mu 0 3 948 950 949
		f 3 -2571 2572 2573
		mu 0 3 950 948 951
		f 3 2574 -2573 2575
		mu 0 3 952 951 948
		f 3 -2575 2576 2577
		mu 0 3 951 952 953
		f 3 2578 2579 -2578
		mu 0 3 953 954 951
		f 3 2580 -2580 2581
		mu 0 3 955 951 954
		f 3 2582 2583 -2582
		mu 0 3 954 956 955
		f 3 -2583 2584 2585
		mu 0 3 956 954 957
		f 3 -2585 2586 2587
		mu 0 3 957 954 958
		f 3 -2588 2588 2589
		mu 0 3 957 958 959
		f 3 2590 -2590 2591
		mu 0 3 960 957 959
		f 3 -2592 2592 2593
		mu 0 3 960 959 961
		f 3 2594 -2594 2595
		mu 0 3 962 960 961
		f 3 2596 -2596 2597
		mu 0 3 963 962 961
		f 3 2598 2599 -2598
		mu 0 3 961 964 963
		f 3 2600 -2600 2601
		mu 0 3 965 963 964
		f 3 2602 2603 -2602
		mu 0 3 964 966 965
		f 3 2604 2605 -2604
		mu 0 3 966 967 965
		f 3 -2606 2606 2607
		mu 0 3 965 967 968
		f 3 -2608 2608 2609
		mu 0 3 965 968 969
		f 3 -2609 2610 2611
		mu 0 3 969 968 970
		f 3 -2612 2612 2613
		mu 0 3 969 970 971
		f 3 2614 -2613 2615
		mu 0 3 972 971 970
		f 3 2616 -2616 2617
		mu 0 3 973 972 970
		f 3 2618 2619 -2618
		mu 0 3 970 974 973
		f 3 -2617 2620 2621
		mu 0 3 972 973 975
		f 3 2622 2623 -2622
		mu 0 3 975 976 972
		f 3 2624 2625 -2624
		mu 0 3 976 977 972
		f 3 2626 -2625 2627
		mu 0 3 978 977 976
		f 3 2628 -2628 2629
		mu 0 3 979 978 976
		f 3 2630 -2630 2631
		mu 0 3 980 979 976
		f 3 -2631 2632 2633
		mu 0 3 979 980 981
		f 3 2634 2635 -2634
		mu 0 3 981 982 979
		f 3 2636 2637 -2636
		mu 0 3 982 983 979
		f 3 2638 -2637 2639
		mu 0 3 984 983 982
		f 3 2640 -2640 2641
		mu 0 3 985 984 982
		f 3 2642 -2642 2643
		mu 0 3 986 985 982
		f 3 -2643 2644 2645
		mu 0 3 985 986 987
		f 3 2646 2647 -2646
		mu 0 3 987 988 985
		f 3 -2648 2648 2649
		mu 0 3 985 988 989
		f 3 2650 -2649 2651
		mu 0 3 990 989 988
		f 3 2652 2653 -2652
		mu 0 3 988 991 990
		f 3 2654 2655 -2654
		mu 0 3 991 992 990
		f 3 2656 -2656 2657
		mu 0 3 993 990 992
		f 3 2658 2659 -2658
		mu 0 3 992 994 993
		f 3 2660 -2660 2661
		mu 0 3 995 993 994
		f 3 2662 -2662 2663
		mu 0 3 996 995 994
		f 3 2664 -2664 2665
		mu 0 3 997 996 994
		f 3 2666 2667 -2666
		mu 0 3 994 998 997
		f 3 2668 2669 -2668
		mu 0 3 998 999 997
		f 3 2670 -2670 2671
		mu 0 3 1000 997 999
		f 3 2672 -2672 2673
		mu 0 3 1001 1000 999
		f 3 2674 2675 -2674
		mu 0 3 999 1002 1001
		f 3 -2675 2676 2677
		mu 0 3 1002 999 1003
		f 3 2678 2679 -2678
		mu 0 3 1003 1004 1002
		f 3 -2679 2680 2681
		mu 0 3 1004 1003 1005
		f 3 2682 -2681 2683
		mu 0 3 998 1005 1003
		f 3 -2683 2684 2685
		mu 0 3 1005 998 992
		f 3 2686 2687 -2682
		mu 0 3 1005 1006 1004
		f 3 -2687 2688 2689
		mu 0 3 1006 1005 991
		f 3 2690 -2690 2691
		mu 0 3 1007 1006 991
		f 3 2692 2693 -2692
		mu 0 3 991 1008 1007
		f 3 -2673 2694 2695
		mu 0 3 1000 1001 1009
		f 3 -2696 2696 2697
		mu 0 3 1000 1009 1010
		f 3 2698 2699 -2698
		mu 0 3 1010 1011 1000
		f 3 -2699 2700 2701
		mu 0 3 1011 1010 1012
		f 3 2702 -2702 2703
		mu 0 3 1013 1011 1012
		f 3 -2704 2704 2705
		mu 0 3 1013 1012 1014
		f 3 -2706 2706 2707
		mu 0 3 1013 1014 1015
		f 3 -2707 2708 2709
		mu 0 3 1015 1014 1016
		f 3 2710 2711 -2709
		mu 0 3 1014 1017 1016
		f 3 -2712 2712 2713
		mu 0 3 1016 1017 1018
		f 3 2714 2715 -2713
		mu 0 3 1017 1019 1018
		f 3 -2716 2716 2717
		mu 0 3 1018 1019 1020
		f 3 -2717 2718 2719
		mu 0 3 1020 1019 1021
		f 3 -2720 2720 2721
		mu 0 3 1020 1021 1022
		f 3 -2721 2722 2723
		mu 0 3 1022 1021 1023
		f 3 2724 -2724 2725
		mu 0 3 1024 1022 1023
		f 3 2726 2727 -2726
		mu 0 3 1023 1025 1024
		f 3 -2728 2728 2729
		mu 0 3 1024 1025 1026
		f 3 2730 2731 -2730
		mu 0 3 1026 1027 1024
		f 3 2732 -2732 2733
		mu 0 3 1028 1024 1027
		f 3 2734 -2734 2735
		mu 0 3 1029 1028 1027
		f 3 2736 -2736 2737
		mu 0 3 1030 1029 1027
		f 3 2738 2739 -2738
		mu 0 3 1027 1031 1030
		f 3 -2740 2740 2741
		mu 0 3 1030 1031 1032
		f 3 2742 2743 -2735
		mu 0 3 1029 1033 1028
		f 3 2744 2745 -2744
		mu 0 3 1033 1034 1028
		f 3 2746 2747 -2746
		mu 0 3 1034 1022 1028
		f 3 2748 2749 -2745
		mu 0 3 1033 1035 1034
		f 3 2750 2751 -2750
		mu 0 3 1035 1020 1034
		f 3 -2749 2752 2753
		mu 0 3 1035 1033 1036
		f 3 2754 -2754 2755
		mu 0 3 1037 1035 1036
		f 3 2756 -2755 2757
		mu 0 3 1038 1035 1037
		f 3 2758 -2758 2759
		mu 0 3 1039 1038 1037
		f 3 2760 -2759 2761
		mu 0 3 1040 1038 1039
		f 3 2762 -2762 2763
		mu 0 3 1041 1040 1039
		f 3 2764 -2763 2765
		mu 0 3 1042 1040 1041
		f 3 2766 -2766 2767
		mu 0 3 1043 1042 1041
		f 3 2768 -2767 2769
		mu 0 3 1044 1042 1043
		f 3 2770 -2770 2771
		mu 0 3 1045 1044 1043
		f 3 -2771 2772 2773
		mu 0 3 1044 1045 1046
		f 3 2774 2775 -2774
		mu 0 3 1046 995 1044
		f 3 2776 -2776 2777
		mu 0 3 1047 1044 995
		f 3 -2775 2778 2779
		mu 0 3 995 1046 1048
		f 3 2780 -2779 2781
		mu 0 3 1049 1048 1046
		f 3 2782 2783 -2782
		mu 0 3 1046 1050 1049
		f 3 2784 2785 -2784
		mu 0 3 1050 1051 1049
		f 3 2786 -2786 2787
		mu 0 3 1052 1049 1051
		f 3 2788 2789 -2788
		mu 0 3 1051 1053 1052
		f 3 2790 -2790 2791
		mu 0 3 1054 1052 1053
		f 3 2792 2793 -2792
		mu 0 3 1053 1055 1054
		f 3 2794 -2794 2795
		mu 0 3 983 1054 1055
		f 3 2796 2797 -2796
		mu 0 3 1055 978 983
		f 3 -2797 2798 2799
		mu 0 3 978 1055 1056
		f 3 2800 -2799 2801
		mu 0 3 1057 1056 1055
		f 3 -2801 2802 2803
		mu 0 3 1056 1057 1058
		f 3 2804 -2803 2805
		mu 0 3 1059 1058 1057
		f 3 2806 2807 -2806
		mu 0 3 1057 1060 1059
		f 3 2808 -2808 2809
		mu 0 3 1061 1059 1060
		f 3 2810 2811 -2810
		mu 0 3 1060 1062 1061
		f 3 -2811 2812 2813
		mu 0 3 1062 1060 1051
		f 3 -2809 2814 2815
		mu 0 3 1059 1061 1063
		f 3 2816 2817 -2816
		mu 0 3 1063 1064 1059
		f 3 -2817 2818 2819
		mu 0 3 1064 1063 1065
		f 3 2820 2821 -2820
		mu 0 3 1065 1066 1064
		f 3 2822 -2822 2823
		mu 0 3 1067 1064 1066
		f 3 2824 2825 -2824
		mu 0 3 1066 962 1067
		f 3 2826 -2826 2827
		mu 0 3 1068 1067 962
		f 3 -2827 2828 2829
		mu 0 3 1067 1068 1069
		f 3 2830 2831 -2830
		mu 0 3 1069 1058 1067
		f 3 2832 -2829 2833
		mu 0 3 971 1069 1068
		f 3 -2833 2834 2835
		mu 0 3 1069 971 977
		f 3 2836 2837 -2836
		mu 0 3 977 1056 1069
		f 3 -2825 2838 2839
		mu 0 3 962 1066 1070
		f 3 2840 -2839 2841
		mu 0 3 1071 1070 1066
		f 3 2842 -2842 2843
		mu 0 3 1072 1071 1066
		f 3 2844 2845 -2841
		mu 0 3 1071 1073 1070
		f 3 2846 2847 -2846
		mu 0 3 1073 960 1070
		f 3 -2823 -2832 2848
		mu 0 3 1064 1067 1058
		f 3 -2821 2849 -2844
		mu 0 3 1066 1065 1072
		f 3 -2807 2850 2851
		mu 0 3 1060 1057 1053
		f 3 -2805 -2818 -2849
		mu 0 3 1058 1059 1064
		f 3 -2831 -2838 -2804
		mu 0 3 1058 1069 1056
		f 3 -2793 -2851 -2802
		mu 0 3 1055 1053 1057
		f 3 -2791 2852 2853
		mu 0 3 1052 1054 1074
		f 3 2854 2855 -2854
		mu 0 3 1074 1075 1052
		f 3 -2855 2856 2857
		mu 0 3 1075 1074 1076
		f 3 2858 2859 -2858
		mu 0 3 1076 1048 1075
		f 3 -2859 2860 2861
		mu 0 3 1048 1076 993
		f 3 2862 -2857 2863
		mu 0 3 989 1076 1074
		f 3 2864 2865 -2864
		mu 0 3 1074 984 989
		f 3 -2865 -2853 2866
		mu 0 3 984 1074 1054
		f 3 -2789 -2813 -2852
		mu 0 3 1053 1051 1060
		f 3 -2787 -2856 2867
		mu 0 3 1049 1052 1075
		f 3 -2785 2868 -2814
		mu 0 3 1051 1050 1062
		f 3 -2781 -2868 -2860
		mu 0 3 1048 1049 1075
		f 3 -2783 -2773 2869
		mu 0 3 1050 1046 1045
		f 3 -2777 2870 -2769
		mu 0 3 1044 1047 1042
		f 3 2871 -2871 2872
		mu 0 3 1015 1042 1047
		f 3 -2872 2873 -2765
		mu 0 3 1042 1015 1040
		f 3 2874 2875 -2761
		mu 0 3 1040 1016 1038
		f 3 2876 2877 -2757
		mu 0 3 1038 1018 1035
		f 3 -2731 2878 -2739
		mu 0 3 1027 1026 1031
		f 3 2879 -2727 2880
		mu 0 3 1077 1025 1023
		f 3 2881 -2881 2882
		mu 0 3 1078 1077 1023
		f 3 2883 2884 -2882
		mu 0 3 1078 1079 1077
		f 3 -2884 2885 2886
		mu 0 3 1079 1078 1080
		f 3 2887 2888 -2886
		mu 0 3 1078 1081 1080
		f 3 2889 -2889 2890
		mu 0 3 1082 1080 1081
		f 3 2891 -2891 2892
		mu 0 3 1083 1082 1081
		f 3 2893 2894 -2893
		mu 0 3 1081 1084 1083
		f 3 2895 -2895 2896
		mu 0 3 1085 1083 1084
		f 3 2897 -2897 2898
		mu 0 3 1017 1085 1084
		f 3 -2896 2899 2900
		mu 0 3 1083 1085 1086
		f 3 2901 -2900 2902
		mu 0 3 1012 1086 1085
		f 3 2903 2904 -2901
		mu 0 3 1086 1087 1083
		f 3 2905 2906 -2904
		mu 0 3 1086 1088 1087
		f 3 2907 -2906 2908
		mu 0 3 1010 1088 1086
		f 3 -2894 2909 2910
		mu 0 3 1084 1081 1089
		f 3 2911 2912 -2911
		mu 0 3 1089 1019 1084
		f 3 -2892 -2905 2913
		mu 0 3 1082 1083 1087
		f 3 -2890 2914 2915
		mu 0 3 1080 1082 1090
		f 3 -2916 2916 2917
		mu 0 3 1080 1090 1091
		f 3 -2888 2918 -2910
		mu 0 3 1081 1078 1089
		f 3 2919 2920 -2919
		mu 0 3 1078 1021 1089
		f 3 2921 -2887 -2918
		mu 0 3 1091 1079 1080
		f 3 -2733 -2748 -2725
		mu 0 3 1024 1028 1022
		f 3 -2920 -2883 -2723
		mu 0 3 1021 1078 1023
		f 3 -2747 -2752 -2722
		mu 0 3 1022 1034 1020
		f 3 -2912 -2921 -2719
		mu 0 3 1019 1089 1021
		f 3 -2751 -2878 -2718
		mu 0 3 1020 1035 1018
		f 3 -2899 -2913 -2715
		mu 0 3 1017 1084 1019
		f 3 -2877 -2876 -2714
		mu 0 3 1018 1038 1016
		f 3 2922 -2898 -2711
		mu 0 3 1014 1085 1017
		f 3 -2875 -2874 -2710
		mu 0 3 1016 1040 1015
		f 3 2923 -2708 -2873
		mu 0 3 1047 1013 1015
		f 3 -2924 2924 2925
		mu 0 3 1013 1047 996
		f 3 -2705 -2903 -2923
		mu 0 3 1014 1012 1085
		f 3 2926 -2703 -2926
		mu 0 3 996 1011 1013
		f 3 -2902 -2701 -2909
		mu 0 3 1086 1012 1010
		f 3 -2908 -2697 2927
		mu 0 3 1088 1010 1009
		f 3 -2671 -2700 2928
		mu 0 3 997 1000 1011
		f 3 -2669 -2684 -2677
		mu 0 3 999 998 1003
		f 3 -2665 -2929 -2927
		mu 0 3 996 997 1011
		f 3 -2663 -2925 -2778
		mu 0 3 995 996 1047
		f 3 -2661 -2780 -2862
		mu 0 3 993 995 1048
		f 3 -2659 -2685 -2667
		mu 0 3 994 992 998
		f 3 -2657 -2861 2929
		mu 0 3 990 993 1076
		f 3 -2689 -2686 -2655
		mu 0 3 991 1005 992
		f 3 -2693 -2653 2930
		mu 0 3 1008 991 988
		f 3 -2863 -2651 -2930
		mu 0 3 1076 989 990
		f 3 -2647 2931 -2931
		mu 0 3 988 987 1008
		f 3 -2866 -2641 -2650
		mu 0 3 989 984 985
		f 3 -2795 -2639 -2867
		mu 0 3 1054 983 984
		f 3 -2635 2932 -2644
		mu 0 3 982 981 986
		f 3 -2798 -2629 -2638
		mu 0 3 983 978 979
		f 3 -2837 -2627 -2800
		mu 0 3 1056 977 978
		f 3 -2623 2933 -2632
		mu 0 3 976 975 980
		f 3 -2835 -2615 -2626
		mu 0 3 977 971 972
		f 3 2934 -2614 -2834
		mu 0 3 1068 969 971
		f 3 -2935 2935 2936
		mu 0 3 969 1068 963
		f 3 -2619 -2611 2937
		mu 0 3 974 970 968
		f 3 2938 2939 -2938
		mu 0 3 968 1092 974
		f 3 -2939 -2607 2940
		mu 0 3 1092 968 967
		f 3 2941 2942 -2941
		mu 0 3 967 1093 1092
		f 3 -2942 2943 2944
		mu 0 3 1093 967 1094
		f 3 2945 2946 -2945
		mu 0 3 1094 1095 1093
		f 3 -2946 2947 2948
		mu 0 3 1095 1094 1096
		f 3 2949 2950 -2948
		mu 0 3 1094 1097 1096
		f 3 2951 2952 -2951
		mu 0 3 1097 1098 1096
		f 3 -2953 2953 2954
		mu 0 3 1096 1098 1099
		f 3 2955 2956 -2954
		mu 0 3 1098 935 1099
		f 3 2957 -2956 2958
		mu 0 3 1100 935 1098
		f 3 2959 2960 -2959
		mu 0 3 1098 1101 1100
		f 3 2961 -2961 2962
		mu 0 3 953 1100 1101
		f 3 2963 2964 -2963
		mu 0 3 1101 958 953
		f 3 -2964 2965 2966
		mu 0 3 958 1101 1102
		f 3 2967 -2966 2968
		mu 0 3 1097 1102 1101
		f 3 -2968 2969 2970
		mu 0 3 1102 1097 966
		f 3 2971 -2955 2972
		mu 0 3 1103 1096 1099
		f 3 2973 2974 -2973
		mu 0 3 1099 1104 1103
		f 3 -2974 2975 2976
		mu 0 3 1104 1099 934
		f 3 2977 -2977 2978
		mu 0 3 1105 1104 934
		f 3 -2978 2979 2980
		mu 0 3 1104 1105 1106
		f 3 2981 2982 -2980
		mu 0 3 1105 1107 1106
		f 3 2983 2984 -2983
		mu 0 3 1107 1108 1106
		f 3 2985 -2984 2986
		mu 0 3 858 1108 1107
		f 3 -2987 2987 2988
		mu 0 3 858 1107 863
		f 3 2989 2990 -2988
		mu 0 3 1107 1109 863
		f 3 2991 2992 -2990
		mu 0 3 1107 1110 1109
		f 3 2993 -2993 2994
		mu 0 3 918 1109 1110
		f 3 -2994 2995 2996
		mu 0 3 1109 918 1111
		f 3 2997 -2997 2998
		mu 0 3 864 1109 1111
		f 3 2999 -2999 3000
		mu 0 3 1112 864 1111
		f 3 -3001 3001 3002
		mu 0 3 1112 1111 916
		f 3 -2992 3003 3004
		mu 0 3 1110 1107 1113
		f 3 3005 3006 -3005
		mu 0 3 1113 920 1110
		f 3 -3006 3007 3008
		mu 0 3 920 1113 930
		f 3 3009 -3004 -2982
		mu 0 3 1105 1113 1107
		f 3 -3010 3010 3011
		mu 0 3 1113 1105 932
		f 3 -2960 -2952 -2969
		mu 0 3 1101 1098 1097
		f 3 -2970 -2950 3012
		mu 0 3 966 1097 1094
		f 3 -2972 3013 -2949
		mu 0 3 1096 1103 1095
		f 3 -2944 -2605 -3013
		mu 0 3 1094 967 966
		f 3 -2603 3014 -2971
		mu 0 3 966 964 1102
		f 3 3015 -3015 3016
		mu 0 3 959 1102 964
		f 3 -2601 -2610 -2937
		mu 0 3 963 965 969
		f 3 -2597 -2936 -2828
		mu 0 3 962 963 1068
		f 3 -2595 -2840 -2848
		mu 0 3 960 962 1070
		f 3 -2599 -2593 -3017
		mu 0 3 964 961 959
		f 3 3017 -2591 -2847
		mu 0 3 1073 957 960
		f 3 -3016 -2589 -2967
		mu 0 3 1102 959 958
		f 3 -3018 3018 -2586
		mu 0 3 957 1073 956
		f 3 -2587 -2579 -2965
		mu 0 3 958 954 953
		f 3 -2962 -2577 3019
		mu 0 3 1100 953 952
		f 3 3020 3021 -3020
		mu 0 3 952 936 1100
		f 3 -3021 3022 3023
		mu 0 3 936 952 947
		f 3 -2581 3024 -2574
		mu 0 3 951 955 950
		f 3 -2567 -3023 -2576
		mu 0 3 948 947 952
		f 3 -2565 3025 3026
		mu 0 3 947 943 938
		f 3 -2569 3027 -2564
		mu 0 3 946 949 945
		f 3 -2558 -2549 -3026
		mu 0 3 943 940 938
		f 3 -2547 3028 3029
		mu 0 3 937 939 931
		f 3 -3027 -2545 -3024
		mu 0 3 947 938 936
		f 3 -2958 -3022 -2541
		mu 0 3 935 1100 936
		f 3 -2539 -2976 -2957
		mu 0 3 935 934 1099
		f 3 -2537 -3011 -2979
		mu 0 3 934 932 1105
		f 3 -2535 -2544 -3030
		mu 0 3 931 933 937
		f 3 -2533 -3008 -3012
		mu 0 3 932 930 1113
		f 3 -2531 -3029 3030
		mu 0 3 929 931 939
		f 3 -2552 -2526 -3031
		mu 0 3 939 928 929
		f 3 -2553 3031 -2524
		mu 0 3 928 941 927
		f 3 3032 3033 -2519
		mu 0 3 926 129 924
		f 3 -2517 -2509 -2527
		mu 0 3 925 922 921
		f 3 -2529 -2507 -3009
		mu 0 3 930 921 920
		f 3 -2505 -2995 -3007
		mu 0 3 920 918 1110
		f 3 -2503 -2512 3034
		mu 0 3 917 919 923
		f 3 3035 -3035 3036
		mu 0 3 1114 917 923
		f 3 -3037 3037 3038
		mu 0 3 1114 923 132
		f 3 -2501 -3002 -2996
		mu 0 3 918 916 1111
		f 3 -2499 -3036 3039
		mu 0 3 915 917 1114
		f 3 3040 -3040 3041
		mu 0 3 1115 915 1114
		f 3 -3042 3042 3043
		mu 0 3 1115 1114 134
		f 3 -2497 3044 -3003
		mu 0 3 916 914 1112
		f 3 3045 -3045 3046
		mu 0 3 1116 1112 914
		f 3 -3046 3047 3048
		mu 0 3 1112 1116 865
		f 3 -2495 -3041 3049
		mu 0 3 913 915 1115
		f 3 3050 3051 -3050
		mu 0 3 1115 1117 913
		f 3 -3051 3052 3053
		mu 0 3 1117 1115 136
		f 3 -2493 3054 -3047
		mu 0 3 914 912 1116
		f 3 3055 -3055 3056
		mu 0 3 1118 1116 912
		f 3 -3056 3057 3058
		mu 0 3 1116 1118 867
		f 3 -2491 -3052 3059
		mu 0 3 911 913 1117
		f 3 3060 3061 -3060
		mu 0 3 1117 1119 911
		f 3 -3061 3062 3063
		mu 0 3 1119 1117 138
		f 3 -2489 3064 -3057
		mu 0 3 912 910 1118
		f 3 3065 -3065 3066
		mu 0 3 1120 1118 910
		f 3 -3066 3067 3068
		mu 0 3 1118 1120 869
		f 3 -2487 -3062 3069
		mu 0 3 909 911 1119
		f 3 3070 3071 -3070
		mu 0 3 1119 1121 909
		f 3 -3071 3072 3073
		mu 0 3 1121 1119 140
		f 3 -2485 3074 -3067
		mu 0 3 910 908 1120
		f 3 3075 -3075 3076
		mu 0 3 1122 1120 908
		f 3 -3076 3077 3078
		mu 0 3 1120 1122 871
		f 3 -2483 -3072 3079
		mu 0 3 907 909 1121
		f 3 3080 3081 -3080
		mu 0 3 1121 1123 907
		f 3 -3081 3082 3083
		mu 0 3 1123 1121 142
		f 3 -2481 3084 -3077
		mu 0 3 908 906 1122
		f 3 3085 -3085 3086
		mu 0 3 1124 1122 906
		f 3 -3086 3087 3088
		mu 0 3 1122 1124 873
		f 3 -2479 -3082 3089
		mu 0 3 905 907 1123
		f 3 3090 3091 -3090
		mu 0 3 1123 1125 905
		f 3 -3091 3092 3093
		mu 0 3 1125 1123 144
		f 3 -2477 3094 -3087
		mu 0 3 906 904 1124
		f 3 3095 3096 -3095
		mu 0 3 904 875 1124
		f 3 -2475 -3092 3097
		mu 0 3 903 905 1125
		f 3 3098 3099 -3098
		mu 0 3 1125 1126 903
		f 3 -3099 3100 3101
		mu 0 3 1126 1125 146
		f 3 3102 -2471 -3100
		mu 0 3 1126 902 903
		f 3 -3103 3103 3104
		mu 0 3 902 1126 1127
		f 3 3105 3106 -3104
		mu 0 3 1126 1128 1127
		f 3 3107 3108 -3107
		mu 0 3 1128 1129 1127
		f 3 -3109 3109 3110
		mu 0 3 1127 1129 1130
		f 3 3111 3112 -3110
		mu 0 3 1129 158 1130
		f 3 3113 -3108 3114
		mu 0 3 153 1129 1128
		f 3 -3106 3115 3116
		mu 0 3 1128 1126 148
		f 3 -3111 3117 -3105
		mu 0 3 1127 1130 902
		f 3 -2469 -3118 3118
		mu 0 3 900 902 1130
		f 3 3119 3120 -3119
		mu 0 3 1130 160 900
		f 3 -3096 -2473 -2467
		mu 0 3 875 904 901
		f 3 -3121 3121 -2463
		mu 0 3 900 160 898
		f 3 -2461 3122 3123
		mu 0 3 899 897 876
		f 3 -2456 -2382 -3123
		mu 0 3 897 878 876
		f 3 -2380 -2450 3124
		mu 0 3 874 877 895
		f 3 -2466 -3124 -2378
		mu 0 3 875 899 876
		f 3 -2376 -3088 -3097
		mu 0 3 875 873 1124
		f 3 -2374 -3125 -2446
		mu 0 3 872 874 895
		f 3 -2372 -3078 -3089
		mu 0 3 873 871 1122
		f 3 -2370 -2447 -2440
		mu 0 3 870 872 894
		f 3 -2368 -3068 -3079
		mu 0 3 871 869 1120
		f 3 -2366 -2441 -2435
		mu 0 3 868 870 893
		f 3 -2364 -3058 -3069
		mu 0 3 869 867 1118
		f 3 -2362 -2436 -2431
		mu 0 3 866 868 892
		f 3 -2360 -3048 -3059
		mu 0 3 867 865 1116
		f 3 -2356 -3000 -3049
		mu 0 3 865 864 1112
		f 3 -2998 -2354 -2991
		mu 0 3 1109 864 863
		f 3 -2358 -2432 -2350
		mu 0 3 862 866 861
		f 3 -2423 -2348 -2429
		mu 0 3 891 860 861
		f 3 -2344 -2989 -2353
		mu 0 3 859 858 863
		f 3 -2986 -2342 3125
		mu 0 3 1108 858 857
		f 3 -2346 3126 -2339
		mu 0 3 856 860 853
		f 3 -2332 -3127 -2424
		mu 0 3 852 853 860
		f 3 -2330 -2426 3127
		mu 0 3 848 852 844
		f 3 3128 -2335 -2328
		mu 0 3 850 854 851
		f 3 -2323 -3128 -2314
		mu 0 3 845 848 844
		f 3 -2417 -2313 -2425
		mu 0 3 890 842 844
		f 3 -2409 -2309 -2415
		mu 0 3 887 841 842
		f 3 -2317 -2310 -2302
		mu 0 3 839 843 840
		f 3 -2300 3129 -2320
		mu 0 3 839 838 847
		f 3 -388 3130 3131
		mu 0 3 195 192 187
		f 3 -2297 -2305 -386
		mu 0 3 194 837 193
		f 3 -2306 3132 -385
		mu 0 3 193 841 191
		f 3 -2448 -381 -3133
		mu 0 3 841 190 191
		f 3 -2396 -378 -2404
		mu 0 3 883 189 190
		f 3 -376 -2394 3133
		mu 0 3 186 189 882
		f 3 -374 -3131 -383
		mu 0 3 188 187 192
		f 3 -3132 -372 -2292
		mu 0 3 195 187 184
		f 3 3134 -370 -3134
		mu 0 3 882 185 186
		f 3 3135 -3135 3136
		mu 0 3 175 185 882
		f 3 -368 3137 3138
		mu 0 3 182 185 177
		f 3 -2291 -2293 -366
		mu 0 3 183 198 184
		f 3 -2288 -364 -2262
		mu 0 3 829 183 181
		f 3 -360 -2250 -2267
		mu 0 3 181 180 825
		f 3 -451 -2247 -358
		mu 0 3 178 223 180
		f 3 -3139 -357 -363
		mu 0 3 182 177 179
		f 3 -354 3139 -450
		mu 0 3 178 176 225
		f 3 3140 -3140 3141
		mu 0 3 170 225 176
		f 3 -353 -3138 -3136
		mu 0 3 175 177 185
		f 3 -348 -3137 -2392
		mu 0 3 174 175 882
		f 3 -347 -2390 -2452
		mu 0 3 173 174 879
		f 3 3142 -344 -2454
		mu 0 3 896 171 173
		f 3 3143 -3143 3144
		mu 0 3 165 171 896
		f 3 -3142 -350 -342
		mu 0 3 170 176 172
		f 3 -338 -453 -3141
		mu 0 3 170 169 225
		f 3 -2243 -454 -336
		mu 0 3 168 226 169
		f 3 -334 -494 -2241
		mu 0 3 168 166 240
		f 3 -333 -341 -3144
		mu 0 3 165 167 171
		f 3 -495 -330 3145
		mu 0 3 242 166 163
		f 3 -328 -3145 -2458
		mu 0 3 164 165 896
		f 3 -327 -2459 3146
		mu 0 3 161 164 898
		f 3 -498 -3146 -324
		mu 0 3 162 242 163
		f 3 -501 -322 3147
		mu 0 3 244 162 159
		f 3 -320 -3147 -3122
		mu 0 3 160 161 898
		f 3 -319 -3120 -3113
		mu 0 3 158 160 1130
		f 3 -2238 -3148 -316
		mu 0 3 157 244 159
		f 3 -3112 3148 -315
		mu 0 3 158 1129 155
		f 3 -2202 -2239 -312
		mu 0 3 156 818 157
		f 3 -310 -560 -2200
		mu 0 3 156 154 270
		f 3 -309 -3149 -3114
		mu 0 3 153 155 1129
		f 3 -561 -306 -2196
		mu 0 3 272 154 152
		f 3 -304 -3115 3149
		mu 0 3 150 153 1128
		f 3 -2194 -2197 -302
		mu 0 3 151 274 152
		f 3 -300 3150 3151
		mu 0 3 151 149 104
		f 3 -298 -3150 -3117
		mu 0 3 148 150 1128
		f 3 -296 3152 3153
		mu 0 3 149 147 106
		f 3 -294 -3116 -3102
		mu 0 3 146 148 1126
		f 3 -292 3154 3155
		mu 0 3 147 145 108
		f 3 -290 -3101 -3094
		mu 0 3 144 146 1125
		f 3 -288 3156 3157
		mu 0 3 145 143 110
		f 3 -286 -3093 -3084
		mu 0 3 142 144 1123
		f 3 -284 3158 3159
		mu 0 3 143 141 112
		f 3 -282 -3083 -3074
		mu 0 3 140 142 1121
		f 3 -280 3160 3161
		mu 0 3 141 139 114
		f 3 -278 -3073 -3064
		mu 0 3 138 140 1119
		f 3 -276 3162 3163
		mu 0 3 139 137 116
		f 3 -274 -3063 -3054
		mu 0 3 136 138 1117
		f 3 -272 3164 3165
		mu 0 3 137 135 118
		f 3 -270 -3053 -3044
		mu 0 3 134 136 1115
		f 3 -268 3166 3167
		mu 0 3 135 133 120
		f 3 -266 -3043 -3039
		mu 0 3 132 134 1114
		f 3 -264 3168 3169
		mu 0 3 133 130 122
		f 3 -262 -3038 -2514
		mu 0 3 131 132 923
		f 3 -2515 -3034 -260
		mu 0 3 131 924 129
		f 3 -258 3170 -3169
		mu 0 3 130 127 122
		f 3 -3033 3171 -257
		mu 0 3 129 926 128
		f 3 -248 3172 3173
		mu 0 3 124 125 1131
		f 3 3174 3175 -3174
		mu 0 3 1131 1132 124
		f 3 3176 3177 -3176
		mu 0 3 1132 1133 124
		f 3 -3177 3178 3179
		mu 0 3 1133 1132 1134
		f 3 3180 -3179 3181
		mu 0 3 1135 1134 1132
		f 3 3182 -3182 3183
		mu 0 3 1136 1135 1132
		f 3 -3183 3184 3185
		mu 0 3 1135 1136 1137
		f 3 3186 3187 -3186
		mu 0 3 1137 1138 1135
		f 3 3188 3189 -3188
		mu 0 3 1138 1139 1135
		f 3 3190 -3189 3191
		mu 0 3 82 1139 1138;
	setAttr ".fc[2000:2155]"
		f 3 3192 -3191 3193
		mu 0 3 87 1139 82
		f 3 -3193 3194 3195
		mu 0 3 1139 87 1140
		f 3 3196 3197 -3196
		mu 0 3 1140 1134 1139
		f 3 -3197 3198 3199
		mu 0 3 1134 1140 1141
		f 3 3200 3201 -3199
		mu 0 3 1140 1142 1141
		f 3 3202 3203 -3202
		mu 0 3 1142 117 1141
		f 3 3204 -3201 3205
		mu 0 3 88 1142 1140
		f 3 3206 -3205 3207
		mu 0 3 1143 1142 88
		f 3 -3207 3208 3209
		mu 0 3 1142 1143 115
		f 3 -3187 3210 3211
		mu 0 3 1138 1137 1144
		f 3 3212 3213 -3212
		mu 0 3 1144 81 1138
		f 3 -3213 3214 3215
		mu 0 3 81 1144 1145
		f 3 -3198 -3181 -3190
		mu 0 3 1139 1134 1135
		f 3 3216 -3180 -3200
		mu 0 3 1141 1133 1134
		f 3 -3217 3217 3218
		mu 0 3 1133 1141 119
		f 3 -3175 3219 -3184
		mu 0 3 1132 1131 1136
		f 3 -246 -3178 3220
		mu 0 3 121 124 1133
		f 3 -244 -3171 -252
		mu 0 3 123 122 127
		f 3 -242 -3167 -3170
		mu 0 3 122 120 133
		f 3 -240 -3221 -3219
		mu 0 3 119 121 1133
		f 3 -238 -3165 -3168
		mu 0 3 120 118 135
		f 3 -236 -3218 -3204
		mu 0 3 117 119 1141
		f 3 -234 -3163 -3166
		mu 0 3 118 116 137
		f 3 -232 -3203 -3210
		mu 0 3 115 117 1142
		f 3 -230 -3161 -3164
		mu 0 3 116 114 139
		f 3 -228 -3209 3221
		mu 0 3 113 115 1143
		f 3 3222 3223 -3222
		mu 0 3 1143 1146 113
		f 3 -3223 3224 3225
		mu 0 3 1146 1143 89
		f 3 -226 -3159 -3162
		mu 0 3 114 112 141
		f 3 -224 -3224 3226
		mu 0 3 111 113 1146
		f 3 3227 3228 -3227
		mu 0 3 1146 1147 111
		f 3 -3228 3229 3230
		mu 0 3 1147 1146 91
		f 3 -222 -3157 -3160
		mu 0 3 112 110 143
		f 3 -220 -3229 3231
		mu 0 3 109 111 1147
		f 3 3232 3233 -3232
		mu 0 3 1147 1148 109
		f 3 -3233 3234 3235
		mu 0 3 1148 1147 93
		f 3 -218 -3155 -3158
		mu 0 3 110 108 145
		f 3 -216 -3234 3236
		mu 0 3 107 109 1148
		f 3 3237 3238 -3237
		mu 0 3 1148 1149 107
		f 3 -3238 3239 3240
		mu 0 3 1149 1148 95
		f 3 -214 -3153 -3156
		mu 0 3 108 106 147
		f 3 -212 -3239 3241
		mu 0 3 105 107 1149
		f 3 3242 3243 -3242
		mu 0 3 1149 1150 105
		f 3 -3243 3244 3245
		mu 0 3 1150 1149 97
		f 3 -210 -3151 -3154
		mu 0 3 106 104 149
		f 3 -208 -3244 3246
		mu 0 3 102 105 1150
		f 3 -206 -2195 -3152
		mu 0 3 104 103 151
		f 3 -2191 -571 -204
		mu 0 3 101 276 103
		f 3 -202 -3247 3247
		mu 0 3 99 102 1150
		f 3 -200 -582 -2192
		mu 0 3 101 100 279
		f 3 -198 -2104 -585
		mu 0 3 100 98 282
		f 3 -196 -3248 -3246
		mu 0 3 97 99 1150
		f 3 -194 -2108 -2105
		mu 0 3 98 96 811
		f 3 -192 -3245 -3241
		mu 0 3 95 97 1149
		f 3 -190 -2110 -2109
		mu 0 3 96 94 809
		f 3 -188 -3240 -3236
		mu 0 3 93 95 1148
		f 3 -186 -882 -2111
		mu 0 3 94 92 409
		f 3 -184 -3235 -3231
		mu 0 3 91 93 1147
		f 3 -182 -888 -883
		mu 0 3 92 90 410
		f 3 -180 -3230 -3226
		mu 0 3 89 91 1146
		f 3 -176 -3225 -3208
		mu 0 3 88 89 1143
		f 3 -174 -3206 -3195
		mu 0 3 87 88 1140
		f 3 -178 -170 -889
		mu 0 3 90 86 85
		f 3 -887 -168 -894
		mu 0 3 411 85 84
		f 3 -164 -173 -3194
		mu 0 3 82 83 87
		f 3 -162 -3192 -3214
		mu 0 3 81 82 1138
		f 3 3248 -161 -3216
		mu 0 3 1145 79 81
		f 3 -3249 3249 3250
		mu 0 3 79 1145 1151
		f 3 -166 -158 -897
		mu 0 3 84 80 78
		f 3 3251 -157 -3251
		mu 0 3 1151 77 79
		f 3 -3252 3252 3253
		mu 0 3 77 1151 1152
		f 3 -896 -154 -901
		mu 0 3 413 78 76
		f 3 3254 -153 -3254
		mu 0 3 1152 75 77
		f 3 -3255 3255 3256
		mu 0 3 75 1152 1153
		f 3 -900 -150 -907
		mu 0 3 414 76 74
		f 3 3257 -149 -3257
		mu 0 3 1153 73 75
		f 3 -3258 3258 3259
		mu 0 3 73 1153 1154
		f 3 -906 -146 -913
		mu 0 3 416 74 72
		f 3 3260 -145 -3260
		mu 0 3 1154 71 73
		f 3 -3261 3261 3262
		mu 0 3 71 1154 1155
		f 3 -912 -142 -919
		mu 0 3 418 72 70
		f 3 3263 -141 -3263
		mu 0 3 1155 69 71
		f 3 -3264 3264 3265
		mu 0 3 69 1155 1156
		f 3 -918 -138 -925
		mu 0 3 420 70 68
		f 3 3266 -137 -3266
		mu 0 3 1156 67 69
		f 3 -3267 3267 3268
		mu 0 3 67 1156 1157
		f 3 -924 -134 -931
		mu 0 3 422 68 66
		f 3 3269 -133 -3269
		mu 0 3 1157 65 67
		f 3 -3270 3270 3271
		mu 0 3 65 1157 1158
		f 3 -930 -130 -937
		mu 0 3 424 66 64
		f 3 3272 -129 -3272
		mu 0 3 1158 63 65
		f 3 -3273 3273 3274
		mu 0 3 63 1158 1159
		f 3 -936 -126 -943
		mu 0 3 426 64 62
		f 3 3275 -125 -3275
		mu 0 3 1159 61 63
		f 3 -3276 3276 3277
		mu 0 3 61 1159 1160
		f 3 -942 -122 -949
		mu 0 3 428 62 60
		f 3 3278 -121 -3278
		mu 0 3 1160 59 61
		f 3 -3279 3279 3280
		mu 0 3 59 1160 1161
		f 3 -948 -118 -2087
		mu 0 3 430 60 58
		f 3 3281 -117 -3281
		mu 0 3 1161 57 59
		f 3 -3282 3282 3283
		mu 0 3 57 1161 1162
		f 3 -2086 -114 3284
		mu 0 3 461 58 55
		f 3 3285 -113 -3284
		mu 0 3 1162 56 57
		f 3 -3286 3286 3287
		mu 0 3 56 1162 1163
		f 3 3288 -3288 3289
		mu 0 3 1164 56 1163
		f 3 3290 -3289 3291
		mu 0 3 1165 56 1164
		f 3 3292 -3292 3293
		mu 0 3 1166 1165 1164
		f 3 -3293 3294 3295
		mu 0 3 1165 1166 1167
		f 3 3296 3297 -3296
		mu 0 3 1167 53 1165
		f 3 -110 -3291 -3298
		mu 0 3 53 56 1165
		f 3 -1043 -3285 -108
		mu 0 3 54 461 55
		f 3 -1045 -106 -1053
		mu 0 3 462 54 52
		f 3 -3297 3298 -105
		mu 0 3 53 1167 50
		f 3 -1052 -102 -1059
		mu 0 3 464 52 51
		f 3 -1060 -100 3299
		mu 0 3 467 51 48
		f 3 -98 -3299 3300
		mu 0 3 49 50 1167
		f 3 3301 -3300 -94
		mu 0 3 46 467 48
		f 3 -2074 -3302 -90
		mu 0 3 44 467 46
		f 3 -1074 -2075 -86
		mu 0 3 42 473 44
		f 3 -1078 -1075 -82
		mu 0 3 40 472 42
		f 3 -1084 -1079 -78
		mu 0 3 38 474 40
		f 3 -1090 -1085 -74
		mu 0 3 36 476 38
		f 3 -1096 -1091 -70
		mu 0 3 34 478 36
		f 3 -1102 -1097 -66
		mu 0 3 32 480 34
		f 3 -1108 -1103 -62
		mu 0 3 30 482 32
		f 3 -1114 -1109 -58
		mu 0 3 28 484 30
		f 3 -1120 -1115 -54
		mu 0 3 26 486 28
		f 3 -1126 -1121 -50
		mu 0 3 24 488 26
		f 3 3302 -43 3303
		mu 0 3 1168 21 22
		f 3 3304 -3303 3305
		mu 0 3 1169 21 1168
		f 3 3306 -3306 3307
		mu 0 3 1170 1169 1168
		f 3 -3307 3308 3309
		mu 0 3 1169 1170 7
		f 3 3310 -3309 3311
		mu 0 3 1171 7 1170
		f 3 3312 -3312 3313
		mu 0 3 1172 1171 1170
		f 3 3314 3315 -3305
		mu 0 3 1169 1173 21
		f 3 -3315 3316 3317
		mu 0 3 1173 1169 8
		f 3 -3316 3318 -40
		mu 0 3 21 1173 18
		f 3 -38 -1127 -46
		mu 0 3 20 19 24
		f 3 -1124 -36 -2072
		mu 0 3 489 19 17
		f 3 3319 -34 -3319
		mu 0 3 1173 16 18
		f 3 -3320 3320 3321
		mu 0 3 16 1173 10
		f 3 -2071 -32 -1239
		mu 0 3 531 17 15
		f 3 -1238 -28 -2048
		mu 0 3 530 15 14
		f 3 -1387 -1907 -26
		mu 0 3 13 593 14
		f 3 -24 3322 -1389
		mu 0 3 13 11 595
		f 3 3323 -3323 3324
		mu 0 3 2 595 11
		f 3 -22 -30 -3322
		mu 0 3 10 12 16
		f 3 -20 3325 -3325
		mu 0 3 11 9 2
		f 3 -18 -3321 -3318
		mu 0 3 8 10 1173
		f 3 -14 -3317 -3310
		mu 0 3 7 8 1169
		f 3 3326 -13 -3311
		mu 0 3 1171 5 7
		f 3 -16 -10 3327
		mu 0 3 9 6 3
		f 3 -6 3328 -1563
		mu 0 3 0 4 674
		f 3 -4 -3326 -3328
		mu 0 3 3 2 9
		f 3 -2 -1393 -3324
		mu 0 3 2 1 595
		f 3 -1 -1562 -1557
		mu 0 3 1 0 672;
	setAttr ".cd" -type "dataPolyComponent" Index_Data Edge 0 ;
	setAttr ".cvd" -type "dataPolyComponent" Index_Data Vertex 0 ;
	setAttr ".pd[0]" -type "dataPolyComponent" Index_Data UV 0 ;
	setAttr ".hfd" -type "dataPolyComponent" Index_Data Face 0 ;
	setAttr ".ndt" 0;
	setAttr ".vcs" 2;
createNode lightLinker -s -n "lightLinker1";
	rename -uid "77E0E847-4DF3-D1F7-04D3-DAB87AC0378A";
	setAttr -s 2 ".lnk";
	setAttr -s 2 ".slnk";
createNode displayLayerManager -n "layerManager";
	rename -uid "AB534529-4CF4-E10B-6104-8A8E9F9644CB";
createNode displayLayer -n "defaultLayer";
	rename -uid "BC789204-4DAD-119E-32C8-93A72643A18F";
	setAttr ".ufem" -type "stringArray" 0  ;
createNode renderLayerManager -n "renderLayerManager";
	rename -uid "A9367825-4631-2733-D357-64BCD21D3802";
createNode renderLayer -n "defaultRenderLayer";
	rename -uid "D9A6C494-41DC-7D59-9724-798FE202BE29";
	setAttr ".g" yes;
createNode skinCluster -n "Cape_skinCluster";
	rename -uid "71901E2B-40B7-C629-712B-84A0BD9353AB";
	setAttr -s 1174 ".wl";
	setAttr ".wl[0:175].w"
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		3 3 0.99298084984417168 10 0.0035095750779141448 11 0.0035095750779141448
		3 3 0.99415579478773619 10 0.0029297321168528919 11 0.0029144730954109499
		3 3 0.98010223556252818 10 0.0099488822187359504 11 0.0099488822187359504
		3 3 0.98313878135497168 10 0.0084382387169033533 11 0.0084229799281250704
		3 3 0.9375295621575237 4 0.039215687589318142 10 0.023254750253158155
		3 3 0.93267719721656217 4 0.047196152935972305 10 0.020126649847465476
		4 3 0.80544746522193744 4 0.13455405931587561 5 0.016311895223795586 
		10 0.043686580238391309
		4 3 0.79804684441078211 4 0.15172045257833824 5 0.011047532087278773 
		10 0.03918517092360084
		4 3 0.59697871955500004 4 0.2178683115700758 5 0.11827267618274184 
		10 0.066880292692182264
		4 3 0.58271152215236066 4 0.22809186747738619 5 0.12819103992127656 
		10 0.061005570448976532
		4 3 0.40299076442406723 4 0.28966200783345114 5 0.21670863355262032 
		10 0.090638594189861324
		4 3 0.3821469516892213 4 0.2759594002667114 5 0.2592965643160301 
		10 0.082597083728037146
		4 3 0.25136187485335859 4 0.3529106650284628 5 0.28218507556479366 
		10 0.11354238455338489
		4 3 0.24315250866519267 4 0.31183337468281297 5 0.33929961161390815 
		10 0.10571450503808622
		4 3 0.15550468862056732 4 0.38408485054969788 5 0.32283511757850647 
		10 0.13757534325122833
		4 3 0.15494011111646724 4 0.34917219952982365 5 0.36655222823393002 
		10 0.12933546111977903
		4 4 0.35030136034341702 5 0.33971161156463042 10 0.16711680840129864 
		35 0.14287021969065397
		4 4 0.36765087198690888 5 0.36369878595618582 10 0.15046921596630239 
		34 0.11818112609060297
		4 3 0.13403524658136437 4 0.36554512926258337 5 0.39484245173398336 
		10 0.1055771724220689
		4 3 0.22355992758929838 4 0.31621270900647774 5 0.37050431414687163 
		10 0.089723049257352208
		4 3 0.19404898439311247 4 0.3282825922348902 5 0.38617533157635231 
		9 0.091493091795644965
		4 3 0.10928511538144114 4 0.36725413525660233 5 0.4211947886556775 
		9 0.10226596070627897
		4 4 0.36046387671041857 5 0.39555962695003666 10 0.12680247048132209 
		34 0.11717402585822266
		4 4 0.3802090585231781 5 0.43456166982650757 9 0.10278477519750595 
		10 0.08244449645280838
		4 3 0.084855423009808528 4 0.36580452595505508 5 0.43189135515608901 
		9 0.11744869587904733
		4 3 0.16598764185598225 4 0.33432516704741988 5 0.39261463577013189 
		9 0.10707255532646592
		4 3 0.14926375115073284 4 0.33937590555751534 5 0.38991378866328774 
		9 0.1214465546284641
		4 3 0.30315097940600677 4 0.30019074454761485 5 0.2965743519621018 
		9 0.10008392408427652
		4 3 0.32347601652145386 4 0.29851225018501282 5 0.27626457810401917 
		9 0.10174715518951416
		4 3 0.60073243900314977 4 0.20970473949196108 5 0.13226519377233245 
		9 0.057297627732556748
		4 3 0.65175860877424996 4 0.15355153324622089 5 0.1348439748032243 
		9 0.059845883176304834
		4 2 0.02459754440633613 3 0.86349279331783058 4 0.07005416654090707 
		5 0.041855495734926279
		4 2 0.023620966645919034 3 0.87060349531022085 4 0.063172347372976334 
		5 0.042603190670883723
		4 2 0.013809414580464363 3 0.94532692432403564 4 0.030380712822079659 
		5 0.010482948273420334
		4 2 0.01344319782966975 3 0.94413672294983553 4 0.032516974410688931 
		5 0.0099031048098058572
		4 2 0.0062714580629911094 3 0.97871366502901735 4 0.013015945093512143 
		5 0.0019989318144793718
		4 2 0.013427939603621484 3 0.93521019187818777 4 0.03912413218650182 
		5 0.012237736331689061
		4 2 0.021988250560927212 3 0.85986114509248524 4 0.079743646976467006 
		5 0.038406957370120558
		4 2 0.021805142293335088 3 0.80666819640740872 4 0.12205691249115856 
		5 0.049469748808097597
		4 3 0.66782634952793751 4 0.13550011712685139 5 0.10731670180472208 
		9 0.089356831540488957
		4 3 0.66356908780657431 4 0.11035324550901915 5 0.12510871793993772 
		9 0.10096894874446877
		4 3 0.45548180085034518 4 0.18439002472452837 5 0.2455634344038623 
		9 0.1145647400212641
		4 3 0.39331653714179993 4 0.20949111878871918 5 0.27905699610710144 
		9 0.11813534796237946
		4 3 0.17750820782047819 4 0.26633096138136031 5 0.40479133136259515 
		9 0.15136949943556635
		4 3 0.14720378816127777 4 0.31891354918479919 5 0.3964751660823822 
		9 0.13740749657154083
		4 3 0.061936371489885234 4 0.33563745271889456 5 0.46379796016065744 
		9 0.13862821563056271
		4 3 0.061432823538780212 4 0.36131837964057922 5 0.43561455607414246 
		9 0.14163424074649811
		4 4 0.35962462961114389 5 0.47736323591117913 9 0.13179217475343011 
		10 0.031219959724246855
		4 4 0.37215229037063663 5 0.46240939656475044 9 0.12593270556779118 
		10 0.039505607496821714
		4 4 0.3809109628200531 5 0.47098496556282043 9 0.11499199271202087 
		10 0.033112078905105591
		4 4 0.39359122221476417 5 0.45577171105316505 9 0.10869001516185689 
		10 0.041947051570213945
		4 4 0.39748227448209272 5 0.45966276355213387 9 0.10588235368623453 
		10 0.036972608279538868
		4 4 0.40311283924352331 5 0.44411383237241514 9 0.10127412791892475 
		10 0.051499200465136778
		4 4 0.39948120266778914 5 0.44351872306109902 9 0.10785076646673568 
		10 0.049149307804376173
		4 4 0.402777141374009 5 0.410788124960484 9 0.1096208186391118 
		10 0.076813915026395244
		4 4 0.38179597827488154 5 0.40039674044246587 9 0.13304341037636117 
		10 0.084763870906291464
		4 4 0.37033646746968535 5 0.33211260539125492 9 0.15188830864595906 
		10 0.14566261849310072
		4 4 0.3103532446868234 5 0.29437705435787059 9 0.21405355313340496 
		10 0.18121614782190101
		4 4 0.27115282820392889 5 0.24892042948187038 10 0.27438772133570494 
		34 0.2055390209784958
		4 4 0.29561302065849304 5 0.29437705874443054 10 0.21080338954925537 
		34 0.19920653104782104
		4 4 0.22636758606530469 5 0.17732509442195016 10 0.30594339054991632 
		34 0.29036392896282887
		4 4 0.19969481676134804 5 0.098222324957452534 10 0.39932859836508183 
		34 0.30275425991611765
		4 4 0.22548256814479828 5 0.16879530251026154 9 0.24640268087387085 
		10 0.35931944847106934
		3 9 0.26059356331825256 10 0.4758983850479126 34 0.26350805163383484
		4 4 0.15304799377918243 5 0.055573359131813049 9 0.35883116722106934 
		10 0.43254747986793518
		4 4 0.24412909877685007 5 0.22114900413599622 9 0.27795834177608314 
		10 0.25676355531107053
		4 4 0.16575875507834356 5 0.10101472360607855 9 0.38793011632717883 
		10 0.34529640498839903
		4 4 0.26616311073303223 5 0.31578546762466431 9 0.25757229328155518 
		10 0.16047912836074829
		4 4 0.33566796279448324 5 0.37456321158165923 9 0.17944609851470442 
		10 0.11032272710915317
		4 4 0.33092239992204903 5 0.41634241366896652 9 0.17381552120768309 
		10 0.078919665201301351
		4 4 0.37062638998031616 5 0.43804073333740234 9 0.13284504413604736 
		10 0.058487832546234131
		4 4 0.35468071302755871 5 0.46053254089654377 9 0.13804836416935515 
		10 0.046738381906542385
		4 4 0.38713664537550219 5 0.46176851655856749 9 0.11322194548737156 
		10 0.037872892578558859
		4 4 0.37293049970962477 5 0.48474860552511068 9 0.11642633465250085 
		10 0.025894560112763643
		4 4 0.37576866289887079 5 0.47780576526301266 9 0.11490043295510274 
		10 0.031525138883013795
		4 4 0.34453344024221005 5 0.51818114036525464 9 0.11667048077405914 
		10 0.020614938618476145
		4 4 0.36470588294460493 5 0.49544518170897478 9 0.11561760814526362 
		10 0.024231327201156692
		4 3 0.01145952554651135 4 0.31883725167620275 5 0.54140537372150976 
		9 0.12829784905577621
		4 3 0.026749064996378132 4 0.33305868320320536 5 0.50864422037092472 
		9 0.13154803142949176
		4 3 0.032806895428844574 4 0.28950941346951264 5 0.53441673119055688 
		9 0.14326695991108596
		4 3 0.076539255108391824 4 0.28711375380222681 5 0.48622873063215066 
		9 0.15011826045723065
		4 3 0.10084687693014271 4 0.28241398299305182 5 0.45879300403312584 
		9 0.15794613604367966
		4 3 0.23590448147200821 4 0.24742503095529927 5 0.36850538300714814 
		9 0.14816510456554435
		4 3 0.27122912215037825 4 0.28017089188353556 5 0.32869458688340464 
		9 0.11990539908268152
		4 3 0.47649347427119704 4 0.21051347098862028 5 0.21016250394163649 
		9 0.10283055079854614
		4 3 0.49555199323022381 4 0.27075609010026419 5 0.20309757770211742 
		9 0.03059433896739459
		4 3 0.6892194930862221 4 0.19261463497720388 5 0.11062791492128332 
		9 0.0075379570152906469
		4 3 0.38863203508603628 4 0.33870450166917593 5 0.22874799711626764 
		36 0.04391546612852016
		4 3 0.23421072959899902 4 0.39198902249336243 5 0.31514456868171692 
		36 0.058655679225921631
		4 3 0.19638360817301712 4 0.41803615818132295 5 0.32521554464233432 
		36 0.060364689003325749
		4 3 0.099656671285629272 4 0.44386968016624451 5 0.38788434863090515 
		36 0.068589299917221069
		4 3 0.086579686603252784 4 0.4368963176474524 5 0.39986267090048389 
		36 0.076661324848810955
		4 3 0.037735562349830991 4 0.44879835342468671 5 0.43546196331685078 
		36 0.078004120908631527
		4 3 0.044373235935371576 4 0.4467383854577186 5 0.43715571705764955 
		36 0.071732661549260293
		4 3 0.014785991623591834 4 0.44844739543308293 5 0.46024261790671567 
		36 0.076523995036609588
		4 3 0.018051423266913169 4 0.43210497820455562 5 0.47673762199832226 
		36 0.073105976530209005
		3 4 0.44675365423227587 5 0.47342640514244438 36 0.079819940625279695
		4 4 0.4112001359462738 5 0.48336002230644226 36 0.068329900503158569 
		37 0.037109941244125366
		4 4 0.41260395222537133 5 0.47937742768558539 36 0.074052037187889913 
		37 0.033966582901153397
		4 4 0.41335165269662633 5 0.47902646393127862 9 0.028625925842900243 
		36 0.078995957529194888
		4 4 0.40270083992667183 5 0.47624933542218306 36 0.087663083941999509 
		37 0.033386740709145588
		4 4 0.38606851573905876 5 0.48017089664617757 36 0.087693600213274353 
		37 0.046066987401489401
		4 4 0.35642022160008713 5 0.47585261222610331 36 0.11544975724406359 
		37 0.052277408929745917
		4 4 0.33218890428543091 5 0.47038987278938293 36 0.12126344442367554 
		37 0.07615777850151062
		4 4 0.25552758574485779 5 0.45529869198799133 36 0.18379491567611694 
		37 0.10537880659103394
		4 4 0.27690547085764694 5 0.47777523522581378 36 0.17557030523783776 
		37 0.069748988678701482
		4 4 0.35956358909606934 5 0.48783093690872192 36 0.11590752750635147 
		37 0.036697946488857269
		4 4 0.26515603164269042 5 0.52037841275475338 36 0.16893263224114713 
		37 0.045532923361409169
		4 4 0.31317616209036475 5 0.53997100606495896 9 0.032135502222228843 
		36 0.11471732962244741
		4 4 0.22365148448814259 5 0.57822537637585925 6 0.0455786997287672 
		36 0.15254443940723106
		3 4 0.1388113179980022 5 0.54990463629507069 6 0.069245441716232273;
	setAttr ".wl[175:309].w"
		1 36 0.24203860399069482
		4 4 0.14424353515557495 5 0.48772411448380093 36 0.26868086452750417 
		37 0.099351485833119924
		4 4 0.03407339802493748 5 0.48886854184968087 36 0.34821087640838139 
		37 0.12884718371700024
		4 4 0.028366520578168027 5 0.39787899854959552 36 0.37830167445090901 
		37 0.19545280642132751
		4 4 0.0034637979931314805 5 0.3529717051973984 36 0.4246280520023345 
		37 0.2189364448071357
		4 4 0.0017853055660702198 5 0.25996795363250363 36 0.43819332235030051 
		37 0.30005341845112565
		3 5 0.30308994650840759 36 0.45282673835754395 37 0.24408331513404846
		4 4 0.0048981461852608136 5 0.47441824541622674 6 0.14653238428962945 
		36 0.37415122410888302
		3 5 0.44277104075594187 6 0.2118409989499897 36 0.34538796029406843
		4 4 0.0048523689642792425 5 0.54695963885027898 6 0.21474021683202135 
		36 0.23344777535342043
		4 4 0.034653238693973132 5 0.56145572244036412 6 0.13403524358544316 
		36 0.26985579528021963
		4 4 0.02836652184625035 5 0.611306923964826 6 0.17953765927367388 
		36 0.1807888949152498
		4 4 0.0038910505836575876 5 0.5864042045051242 6 0.27702754742396707 
		36 0.13267719748725118
		4 4 0.021255817818607109 5 0.6459601689939245 6 0.2171816584478006 
		36 0.11560235473966779
		4 4 0.084260323409144924 5 0.64605171451049626 6 0.12133974762767177 
		36 0.14834821445268712
		4 4 0.061676966280718282 5 0.67803464551924719 6 0.14357213301582289 
		36 0.11671625518421164
		4 4 0.01515220873284651 5 0.66829938692300606 6 0.24364079898060559 
		36 0.072907605363541919
		4 4 0.0028076600126494093 5 0.60875868457131832 6 0.30699625439757711 
		7 0.081437401018455244
		4 4 0.0020447089003562875 5 0.62412451680546721 6 0.31630426129761657 
		7 0.057526512996559982
		3 5 0.53371482292242611 6 0.34050505845986218 7 0.12578011861771168
		3 5 0.52439154757236095 6 0.31509880170520549 7 0.16050965072243364
		3 5 0.4573739239182163 6 0.33243304986406935 7 0.21019302621771435
		3 5 0.45650415932380917 6 0.31964599609902505 7 0.22384984457716578
		3 5 0.4945296273450609 6 0.30966659918924272 36 0.19580377346569638
		3 5 0.42716106772422791 6 0.31085678935050964 7 0.26198214292526245
		3 5 0.40595102310180664 6 0.22812238335609436 36 0.365926593542099
		3 5 0.33171588182449341 6 0.34160372614860535 36 0.32668039202690125
		3 5 0.27682917897657783 6 0.24539558223790553 36 0.47777523878551664
		4 5 0.11729610141062888 6 0.10273899291066815 36 0.4900892747951936 
		37 0.28987563088350937
		4 5 0.080827042460441589 6 0.18464942276477814 36 0.4762951135635376 
		37 0.25822842121124268
		4 5 0.11644159083900466 6 0.26941328839341866 7 0.2283512617893329 
		36 0.38579385897824381
		4 5 0.064881361537565574 6 0.26402684849480651 7 0.22623026202447516 
		36 0.4448615279431527
		4 5 0.033112077918288768 6 0.17402913647803259 36 0.50267796210414284 
		37 0.29018082349953583
		4 5 0.03077744784287953 6 0.098344396005403872 36 0.52536811010146467 
		37 0.34551004605025193
		4 5 0.030502784656329624 6 0.097154191540693588 36 0.51453422925024228 
		37 0.35780879455273457
		3 5 0.033829252788842627 36 0.52996110323860013 37 0.43620964397255729
		4 5 0.013061722229614544 6 0.048142211491267309 36 0.52172122345092575 
		37 0.41707484282819235
		4 5 0.010421912117904625 36 0.48480963390910303 37 0.45413902105859189 
		61 0.050629432914400446
		4 5 0.002990768332836707 36 0.49628443219164992 37 0.4656900828567811 
		61 0.035034716618732316
		4 5 0.0045624476216635087 36 0.50603495284608258 37 0.46434728691275268 
		61 0.025055312619501197
		3 36 0.4876478214485086 37 0.48763256265975874 61 0.024719615891732695
		4 5 0.0043030441558326608 36 0.4883039573232012 37 0.48802929912122728 
		61 0.0193636993997389
		4 5 0.021377889001449983 36 0.50595866597155981 37 0.45163651375472236 
		61 0.021026931272267842
		4 5 0.022812238005571511 36 0.47711908906161615 37 0.47611200898161532 
		61 0.023956663951197013
		4 5 0.070054166149448913 36 0.48422980398727544 37 0.42197299082199669 
		61 0.023743039041278956
		4 4 0.0012054627522925109 5 0.071671628813585714 36 0.46356908361173604 
		37 0.46355382482238577
		4 4 0.0010223544661265185 5 0.15353627492193858 36 0.44756236641139557 
		37 0.39787900420053934
		4 4 0.0089112687689973623 5 0.20256350896775069 36 0.41202410978819409 
		37 0.37650111247505785
		4 4 0.01550316627231085 5 0.3088273411781105 36 0.39616999103905631 
		37 0.27949950151052233
		4 4 0.074753946999058518 5 0.34476235252050791 36 0.33281451215733204 
		37 0.24766918832310147
		4 4 0.12343022696457295 5 0.42290379651850918 36 0.29404135881271903 
		37 0.15962461770419886
		4 4 0.18800641596317291 5 0.40846875309944153 36 0.22600136697292328 
		37 0.17752346396446228
		4 4 0.04736400430920723 5 0.23912413596454363 36 0.36774242198275342 
		37 0.34576943774349567
		4 4 0.13092240691184998 5 0.32500189542770386 36 0.27698177099227905 
		37 0.26709392666816711
		4 4 0.044449531866596101 5 0.11396963488965138 36 0.42078278722711765 
		37 0.4207980460166349
		4 4 0.0096437019981319427 5 0.10624857424988815 36 0.44205386187598994 
		37 0.44205386187598994
		4 5 0.035461965948343277 36 0.45705348253250122 37 0.45705348253250122 
		61 0.050431068986654282
		4 5 0.022812238090553719 36 0.47092393303806307 37 0.47092393303806296 
		61 0.035339895833320333
		4 5 0.037460896140984176 36 0.44255741276628563 37 0.44255741276628563 
		61 0.077424278326444523
		4 4 0.10765239596366882 5 0.1740138828754425 36 0.35916686058044434 
		37 0.35916686058044434
		4 5 0.031601433534957597 36 0.4188906659641663 37 0.43247119720018795 
		61 0.11703670330068813
		4 4 0.17822538316249847 5 0.221957728266716 36 0.29069963097572327 
		37 0.30911725759506226
		4 4 0.21750210549685517 5 0.37766078677268011 36 0.204257267776985 
		37 0.20057983995347978
		4 4 0.27765316184838357 5 0.4453803367224386 36 0.15158312248562458 
		37 0.12538337894355325
		4 4 0.31714350221413001 5 0.46631571997937349 36 0.1149156921723164 
		37 0.10162508563418005
		4 4 0.34717326839010015 5 0.48197146531982027 36 0.10054169445422748 
		37 0.070313571835852087
		4 4 0.35483329695090732 5 0.49147783611391849 36 0.085801480282810025 
		37 0.067887386652364129
		4 4 0.39101243019104004 5 0.48783093690872192 36 0.075303271412849426 
		37 0.045853361487388611
		4 4 0.37189287362873041 5 0.49428549961319751 36 0.077943087495227395 
		37 0.055878539262844688
		4 4 0.40567635885363285 5 0.48195620653098514 36 0.06797893989117533 
		37 0.044388494724206702
		4 4 0.364675372838974 5 0.4930342435836792 36 0.07611200213432312 
		37 0.066178381443023682
		4 4 0.35603875717607342 5 0.49071488881218928 36 0.07884336439170013 
		37 0.074402989620037149
		4 4 0.34854656717588428 5 0.48407721880135846 37 0.088761732643557578 
		61 0.07861448137919963
		4 4 0.3492179811000824 5 0.48665598034858704 37 0.084382392466068268 
		61 0.079743646085262299
		4 4 0.32263675812835629 5 0.4755626689726512 37 0.10186923447056465 
		61 0.099931338428427857
		4 4 0.31760128859279618 5 0.44899671600763924 37 0.1204852369355375 
		61 0.11291675846402707
		4 4 0.34253451993766099 5 0.45975432827519613 36 0.08839551556994428 
		37 0.10931563621719859
		4 4 0.30690470795191388 5 0.38324559305974237 37 0.16726939629419738 
		61 0.14258030269414637
		4 4 0.29781031608581543 5 0.37793546915054321 37 0.16383612155914307 
		61 0.16041809320449829
		4 4 0.31921872496604919 5 0.33133441209793091 37 0.18196383118629456 
		61 0.16748303174972534
		4 4 0.31261157523674404 5 0.32149233935039728 37 0.21069657488619425 
		61 0.15519951052666439
		4 4 0.31241321563720703 5 0.27743953466415405 37 0.22355993092060089 
		61 0.18658731877803802
		4 4 0.32185855507850647 5 0.31038376688957214 37 0.18599221110343933 
		61 0.18176546692848206
		4 4 0.30757609009742737 5 0.34296178817749023 37 0.1747615784406662 
		61 0.1747005432844162
		4 4 0.32236209992113857 5 0.32826734078328829 37 0.17607385182490723 
		61 0.17329670747066597
		4 4 0.31767758253697181 5 0.35175096464528205 37 0.16987868890347049 
		61 0.1606927639142757
		4 4 0.2958266481135286 5 0.37546349131261547 37 0.16513313599129223 
		61 0.1635767245825637
		4 4 0.30516518071786108 5 0.3814755493842229 37 0.16449225439108175 
		61 0.14886701550683426
		4 4 0.28735790084835738 5 0.42069122822122618 37 0.14831769687410737 
		61 0.14363317405630907
		4 4 0.29372090976598592 5 0.43218128181044108 37 0.13710230997509687 
		61 0.13699549844847614
		4 4 0.33679712320561889 5 0.46492714382599509 37 0.099290454377091747 
		61 0.098985278591294273
		4 4 0.34608987231619559 5 0.47841611861002531 37 0.087891966759353624 
		61 0.087602042314425421
		4 3 0.13905546172749594 4 0.35547417667116354 5 0.41818875385961496 
		37 0.087281607741725498
		4 3 0.15403982996940613 4 0.37912565469741821 5 0.38663309812545776 
		37 0.080201417207717896
		4 4 0.3678034598798075 5 0.46492714382599509 36 0.084550240405652524 
		37 0.082719155888544851
		4 3 0.16998550549127914 4 0.42626077571899856 5 0.33629358315905306 
		36 0.06746013563066923
		4 3 0.28479438807968505 4 0.3928892881207966 5 0.26906233825488135 
		37 0.05325398554463695
		4 3 0.32341498016038916 4 0.37885099508296327 5 0.25259783769921273 
		36 0.045136187057434815
		4 3 0.47740901583602313 4 0.31660944931081197 5 0.17625695860960242 
		36 0.029724576243562464
		4 3 0.5567712063318967 4 0.26968794458311918 5 0.14567787619655112 
		36 0.027862972888433049
		4 2 0.022049287621574501 3 0.72332341422003488 4 0.17689784101822392 
		5 0.077729457140166686
		4 2 0.01390096915159194 3 0.91015487739787471 4 0.0580453201047232 
		5 0.017898833345810262
		4 2 0.01490806426784444 3 0.86741436174075581 4 0.085130081214979891 
		5 0.032547492776419912
		4 2 0.0072480357755168902 3 0.9700160218522329 4 0.018966963890053316 
		5 0.0037689784821968459
		4 2 0.0064545664560598879 3 0.97621118454139688 4 0.01481651040482969 
		5 0.0025177385977135356
		3 2 0.002563515691179164 3 0.9925230792340608 4 0.0049134050747600645
		3 2 0.0023804074519097086 3 0.99320973492037568 4 0.0044098576277146586
		4 2 0.0063324942742532982 3 0.98002594024856149 4 0.011718928732078554 
		5 0.0019226367451066378
		3 2 0.0023651484457517745 3 0.99363698772981623 4 0.0039978638244320321
		2 3 0.99865720610091602 4 0.0013427938990840077
		2 3 0.998748760228651 4 0.0012512397713489688
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		2 3 0.9984283207826975 4 0.0015716792173024827
		2 3 0.9985198749097931 4 0.0014801250902069421
		3 2 0.0027313649029740779 3 0.99180590529107782 4 0.0054627298059481558
		4 2 0.0029144732426625193 3 0.98966964172904104 4 0.0063630124956069335 
		5 0.0010528725326896012
		4 2 0.0078889143063383457 3 0.95886167582669324 4 0.025635157496719366 
		5 0.0076142523702490807
		4 2 0.0088044555061104913 3 0.94602884007466481 4 0.032043945432241344 
		5 0.013122758986983325
		4 2 0.016647592248944909 3 0.82439917633086135 4 0.10896467458071066 
		5 0.04998855683948307
		4 2 0.018265049836542271 3 0.7928892940547716 4 0.12312504603294638 
		5 0.065720610075739733
		4 3 0.61116959372077861 4 0.23715572721759959 5 0.12516975752552295 
		37 0.026504921536098836
		4 3 0.57563132905410719 4 0.24408331877117334 5 0.14515908278761927 
		37 0.03512626938710018
		4 3 0.40933852625380224 4 0.32808422431192874 5 0.20869764296901147 
		37 0.053879606465257586
		4 3 0.43981078267097473 4 0.32555124163627625 5 0.19374379515647888 
		37 0.040894180536270142
		4 2 0.023437857278617365 3 0.65151446086891796 4 0.21934844226615963 
		5 0.10569923958630503
		4 3 0.26581216056504964 4 0.36014342576372194 5 0.30402076470867367 
		37 0.070023648962554697
		4 3 0.23416494974248186 4 0.34543373666057381 5 0.34699016292407864 
		37 0.073411150672865647
		4 3 0.13739223471152257 4 0.34334325022973305 5 0.42497902158694667 
		37 0.094285493471797696
		4 3 0.22104218602180481 4 0.3339131772518158 5 0.36874952912330627 
		37 0.07629510760307312
		4 3 0.14822614082525565 4 0.34036773189628322 5 0.40151065288848686 
		37 0.10989547438997421
		4 3 0.218005645543421 4 0.3301289428789756 5 0.36978713228981391 
		37 0.082078279287789449
		4 3 0.34847027452815632 4 0.3181048369195853 5 0.27161059087079681 
		37 0.06181429768146162;
	setAttr ".wl[310:643].w"
		4 3 0.37462424673699962 4 0.32133975146204602 5 0.2444342636401316 
		37 0.059601738160822718
		4 3 0.55182726218974709 4 0.24634165030609165 5 0.15815976556688111 
		37 0.043671321937280183
		4 3 0.76664377258439809 4 0.13179217450794806 5 0.081406884956822162 
		37 0.020157167950831681
		4 3 0.75158311476449347 4 0.13571374396393296 5 0.086198219932951819 
		37 0.026504921338621777
		4 2 0.016342412558627034 3 0.9175249865835533 4 0.042511634211900573 
		5 0.023620966645919034
		4 2 0.010040436992911324 3 0.93434042869734169 4 0.03691157370791813 
		5 0.018707560601828887
		4 2 0.0037994964513927698 3 0.9843900203704834 4 0.00871290173381567 
		5 0.0030975814443081617
		4 2 0.0032959486698293946 3 0.98712138552024342 4 0.0075532159345230027 
		5 0.0020294498754042105
		3 2 0.001037613504678591 3 0.99710078579575101 4 0.0018616006995704132
		2 3 0.9983367666558578 4 0.0016632333441422241
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		3 2 0.0011902037187498408 3 0.99670405124038508 4 0.002105745040865103
		3 2 0.00138857099356928 3 0.99615472647934666 4 0.002456702527084111
		4 2 0.0044098576051261589 3 0.98115510753607948 4 0.010513465959251045 
		5 0.0039215688995432648
		4 2 0.0049744410294520168 3 0.97903410460563112 4 0.01240558429767393 
		5 0.0035858700672430181
		3 3 0.92820630383030389 4 0.048416874220590121 5 0.023376821949105963
		3 3 0.93064774296159702 4 0.053391319464406437 5 0.015960937573996491
		4 2 0.040177005226764692 3 0.75269703094333706 4 0.13943694168307411 
		5 0.067689022146824165
		4 3 0.54065764554579909 4 0.26497292814746048 5 0.14639505907589637 
		37 0.047974367230844132
		3 3 0.61591516548584779 4 0.26915388697786879 5 0.11493094753628341
		4 3 0.33060195795743197 4 0.32520028706490778 5 0.27925535828429937 
		37 0.064942396693360827
		4 3 0.33191424360935207 4 0.32217898724839844 5 0.27684443982806473 
		37 0.069062329314184712
		4 3 0.22021820484941587 4 0.32753490425542281 5 0.36252384297478668 
		37 0.089723047920374638
		4 3 0.23886472765014388 4 0.32936598869067474 5 0.32721446969466 
		37 0.10455481396452147
		4 3 0.17399862408638 4 0.33789578080177307 5 0.34367895126342773 
		37 0.14442664384841919
		4 3 0.1746700257062912 4 0.3499504029750824 5 0.32578012347221375 
		37 0.14959944784641266
		4 3 0.26483559213823687 4 0.32524606100848225 5 0.29152360124105808 
		37 0.11839474561222277
		4 3 0.38521400668045891 4 0.28189516487561411 5 0.24988174810829383 
		37 0.083009080335633159
		4 3 0.42465856354938025 4 0.2666514197986467 5 0.21359579105976378 
		37 0.095094225592209203
		3 3 0.69417869010301392 4 0.21509116567535452 5 0.090730144221631517
		3 3 0.63433279497423156 4 0.25810635859091158 5 0.10756084643485685
		4 2 0.048767833993437995 3 0.78448157041367939 4 0.12947280463813238 
		5 0.037277790954750201
		4 2 0.044022277653549276 3 0.75899900136886544 4 0.14822614413836813 
		5 0.048752576839217202
		3 3 0.93606469748757581 4 0.0528572524205888 5 0.011078050091835389
		4 3 0.97962920557733979 4 0.012314030737173801 5 0.0021515220583796599 
		37 0.0059052416271067288
		4 3 0.98039215643360633 4 0.011398489568431529 5 0.0014496070774860565 
		37 0.0067597469204761489
		3 2 0.0053406577110955613 3 0.99278248257900514 4 0.0018768597098992972
		3 2 0.0016021972909462305 3 0.99577325095626568 4 0.0026245517527881111
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		2 3 0.99884031435664189 4 0.0011596856433581308
		3 2 0.0020599679128878879 3 0.99473563755595318 4 0.0032043945311589369
		3 2 0.0022583353017049911 3 0.99397268618801715 4 0.0037689785102779246
		3 2 0.0060273138750090135 3 0.98435950187560217 4 0.0096131842493888137
		3 2 0.0056610972128346331 3 0.98666361473508413 4 0.0076752880520813381
		4 3 0.953688867489207 4 0.025589380615865565 5 0.0052796216168224663 
		10 0.015442130278105017
		4 3 0.95057602772791749 4 0.028839551530135503 5 0.0042114901327195324 
		10 0.016372930609227534
		4 3 0.82299535240239874 4 0.11192492228858289 5 0.03031967535138614 
		10 0.034760049957632273
		4 3 0.84386968927036854 4 0.088029295534004626 5 0.03492790101069175 
		10 0.033173114184935071
		4 3 0.56894790066503154 4 0.23260852261244278 5 0.14637979592420541 
		10 0.052063780798320088
		4 3 0.58570229352598313 4 0.22256809224298493 5 0.14030670962884975 
		10 0.051422904602182233
		4 3 0.31813535331290477 4 0.29538414102333888 5 0.30115205273890533 
		9 0.085328452924850973
		4 3 0.34668498714737611 4 0.28862440156006214 5 0.29547568715399969 
		9 0.06921492413856202
		4 3 0.56159305154090333 4 0.23190660601923907 5 0.1512474257406039 
		10 0.05525291669925364
		4 3 0.36000609666113625 4 0.27885863392694765 5 0.28542000267967582 
		10 0.075715266732240216
		4 3 0.56589608752098586 4 0.2315861705885883 5 0.14618143275922427 
		10 0.056336309131201627
		4 3 0.81104753588778822 4 0.12883192012834727 5 0.025116349940381574 
		10 0.035004194043482977
		4 3 0.79218738090712759 4 0.15407034525170407 5 0.017792019727945033 
		10 0.035950254113223341
		4 3 0.94435034599312939 4 0.035324636254605413 5 0.0034180208467651388 
		10 0.01690699690550012
		4 3 0.9280994914448939 4 0.051590750655374711 5 0.0023804073599072322 
		10 0.017929350539824213
		3 3 0.98696879556418482 10 0.0065918973258456285 11 0.0064393071099695725
		3 3 0.982925154192684 4 0.0097962922975335636 10 0.0072785535097824776
		3 3 0.99575799193543479 10 0.0021210040322826038 11 0.0021210040322826038
		3 3 0.99343862046067766 10 0.0032806897696611849 11 0.0032806897696611849
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		3 3 0.99609369039535522 10 0.0019531548023223877 11 0.0019531548023223877
		3 2 0.0019836728290198616 3 0.99552910662382443 4 0.0024872205471556728
		3 3 0.9878995954791574 10 0.0062561989383163926 11 0.005844205582526199
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1;
	setAttr ".wl[644:889].w"
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		3 3 0.99548332956169427 37 0.0022583352191528749 38 0.0022583352191528749
		3 3 0.99455252931224991 37 0.0027313648546422251 38 0.0027161058331079107
		4 3 0.98298619003414922 5 0.0010833905304497805 37 0.0079652097177005093 
		38 0.0079652097177005093
		4 3 0.93450827624938992 4 0.038315404706090378 5 0.0082703904395787665 
		37 0.018905928604940885
		3 2 0.0085297932327782766 3 0.98257419701923998 4 0.0088960097479817528
		4 3 0.94473182385191001 4 0.029678797107479091 5 0.0035858701156672428 
		37 0.022003508924943672
		3 3 0.9667048128332425 4 0.018188754604815168 38 0.015106432561942355
		3 3 0.95982299670865534 4 0.039108871776233185 5 0.0010681315151114933
		4 3 0.84316777554774458 4 0.093827723757716086 5 0.020202945767321095 
		37 0.042801554927218294
		4 3 0.86300450041002663 4 0.081040665016729088 5 0.0067292288469709572 
		37 0.049225605726273325
		4 3 0.65085832809973521 4 0.17279316098705319 5 0.10243381330891371 
		37 0.073914697604297905
		3 0 0.0087129018819056998 3 0.98941023839333742 4 0.0018768597247569728
		3 0 0.0013580529756826712 2 0.0012359807980932176 3 0.99740596622622413
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		4 3 0.84661631199314613 4 0.084855420797030984 5 0.040497443815740872 
		10 0.028030823394082052
		4 2 0.014831769224882985 3 0.9489433134014037 4 0.028732737419259781 
		5 0.0074921799544536323
		4 2 0.014129854449204357 3 0.94795147622476106 4 0.029404134818454306 
		5 0.0085145345075803257
		4 2 0.0061493861645817169 3 0.98165865489422754 4 0.011032273256791002 
		5 0.0011596856843997055
		1 3 1
		4 4 0.34329747642133429 5 0.34120699254859993 37 0.17668421303206364 
		62 0.1388113179980022
		4 4 0.3342641294002533 5 0.35465019941329956 37 0.17221331596374512 
		61 0.13887235522270203
		4 3 0.16437018162563713 4 0.32486457116700068 5 0.38088045091748912 
		37 0.12988479628987307
		4 4 0.3341725766658783 5 0.34042876958847046 37 0.1745174378156662 
		61 0.15088121592998505
		4 4 0.37010756410738499 5 0.47829404829661593 36 0.084321357938061337 
		37 0.067277029657937804
		4 4 0.2601968386798626 5 0.22146945031686799 36 0.2031433612576628 
		37 0.31519034974560661
		4 4 0.24684520065784454 5 0.28197145462036133 36 0.20823986828327179 
		37 0.26294347643852234
		4 4 0.30110627861479339 5 0.40502021320194326 36 0.1295185853469161 
		37 0.16435492283634726
		4 4 0.27411306312848721 5 0.40450141436608755 36 0.15510796241623107 
		37 0.16627756008919417
		4 4 0.33415731538714977 5 0.4719615543487552 36 0.096162355719787207 
		37 0.097718774544307774
		4 4 0.18451209366321564 5 0.13208208978176117 36 0.30795758962631226 
		37 0.37544822692871094
		3 5 0.18040742248903843 36 0.48509956129043641 37 0.33449301622052513
		4 5 0.0063630125015329509 36 0.483131151044352 37 0.48314640983374857 
		61 0.027359426620366542
		4 5 0.091355762014452183 6 0.04431220078003107 36 0.50719463069446935 
		37 0.35713740651104736
		4 5 0.029297321816553756 6 0.045410848815658322 36 0.53168534836407488 
		37 0.39360648100371298
		3 5 0.24495308466185756 36 0.48503852613327691 37 0.27000838920486553
		3 36 0.48969253076755853 37 0.48969253076755853 61 0.020614938464882885
		3 36 0.48599984789267325 37 0.48599984789267325 61 0.028000304214653521
		3 36 0.48186465200288869 37 0.48181887563655384 61 0.036316472360557461
		3 36 0.47943846641506727 37 0.47942320762560686 61 0.041138325959325886
		3 36 0.46848249086378146 37 0.46848249086378146 61 0.063035018272437016
		4 5 0.0015716792465772893 36 0.47203784928264325 37 0.47098496304064658 
		61 0.055405508430132949
		3 5 0.4537422724625807 6 0.37689784730818643 7 0.1693598802292329
		3 5 0.54081023545280449 6 0.37407494148723691 7 0.085114823059958558
		3 5 0.44950026608631211 6 0.44534981582574407 7 0.10514991808794377
		3 5 0.54256504774093628 6 0.3969481885433197 7 0.060486763715744019
		4 4 0.0011596856735992906 5 0.6303654365924084 6 0.32716870582152002 
		7 0.041306171912472274
		4 4 0.0081177997000744552 5 0.67666131699143839 6 0.26329443030344418 
		36 0.051926453005043019
		4 4 0.016449225851996652 5 0.6586251769021596 6 0.2781109177567504 
		9 0.046814679489093354
		4 4 0.0037384604012486054 5 0.62185091402837767 6 0.33574426510301497 
		7 0.038666360467358843
		4 4 0.012161440544465349 5 0.59894712396847705 6 0.34026093209867087 
		7 0.04863050338838678
		3 5 0.53545433482324456 6 0.40610361250528548 7 0.058442052671469943
		3 5 0.42783246081817838 6 0.4989700093711914 7 0.073197529810630227
		3 5 0.44051271348809662 6 0.49073013297669488 7 0.068757153535208448
		4 4 0.0023651484314341194 5 0.51688409682014091 6 0.40627146419899796 
		7 0.074479290549427049
		3 5 0.40891126102888031 6 0.49967193975800228 7 0.09141679921311735
		4 4 0.0017547874968745368 5 0.40379949924680997 6 0.44115358067237942 
		7 0.15329213258393604
		4 4 0.0074158845744552986 5 0.49149310153984982 6 0.38896771921292567 
		7 0.11212329467276921
		4 4 0.027145799350536612 5 0.56310367794000982 6 0.33943694956390913 
		7 0.070313573145544428
		4 4 0.017090104392989691 5 0.46837567934113988 6 0.35909056395969863 
		7 0.15544365230617185
		4 4 0.005767910283665979 5 0.40202945526972805 6 0.38664835745466181 
		7 0.20555427699194423
		4 4 0.013214313708179831 5 0.39148546103776022 6 0.36159304558917882 
		7 0.23370717966488108
		4 4 0.030457008062731324 5 0.43140306265273948 6 0.34714274951922242 
		7 0.19099717976530678
		4 4 0.021606774960445659 5 0.34837871725041658 6 0.37030595472025507 
		7 0.25970855306888269
		4 4 0.042603192416685566 5 0.34222934797430088 6 0.35448233481623609 
		9 0.26068512479277745
		4 4 0.065720609830911381 5 0.46823835024060056 6 0.27196153795747802 
		9 0.19407950197101009
		4 4 0.048462654853657021 5 0.52741282588899707 6 0.32538339132014599 
		7 0.098741127937199982
		4 4 0.085496298331794895 5 0.53461509544689145 6 0.19659723194988643 
		9 0.18329137427142728
		4 4 0.10879682668449858 5 0.47853818179266028 6 0.15167467183117067 
		9 0.26099031969167052
		4 4 0.081452659655715076 5 0.36736094677924402 6 0.20772106790750422 
		9 0.34346532565753662
		4 4 0.13324177364440093 5 0.39812314806970317 6 0.12251468839134788 
		9 0.34612038989454796
		4 4 0.17065690584970195 5 0.49655908716141495 6 0.076874949610791721 
		9 0.25590905737809133
		4 4 0.13789577884894444 5 0.54283970998853226 6 0.098130770758768693 
		9 0.22113374040375455
		4 4 0.19179063963968068 5 0.56197452335814191 6 0.043167773473382839 
		9 0.20306706352879456
		4 4 0.14934004620701005 5 0.60038148462203911 9 0.18985274151187032 
		36 0.060425727659080511
		4 4 0.1884947007241603 5 0.60317386320184663 9 0.16653697502868203 
		36 0.041794461045311038
		4 4 0.15304798864784874 5 0.6350957538341665 9 0.15503166096178833 
		36 0.056824596556196476
		4 4 0.19501030009216891 5 0.61559473092269756 9 0.14206148366492652 
		36 0.047333485320207057
		4 4 0.18939498137457289 5 0.62168306343884427 9 0.12773327577014743 
		36 0.061188679416435507
		4 4 0.23916990698620816 5 0.585336080412029 9 0.12086671410699615 
		36 0.054627298494766677
		4 4 0.25748073671041821 5 0.57750820253032142 9 0.098039215832364329 
		36 0.066971844926896021
		4 4 0.31958496094368455 5 0.55425345071772558 9 0.055634393459045986 
		36 0.070527194879543856
		4 4 0.30589762444010982 5 0.55559623448400286 9 0.059403371287149828 
		36 0.079102769788737481
		4 4 0.25967804177875908 5 0.59107346663788263 9 0.062104219096248275 
		36 0.087144272487110028
		4 4 0.32094299315001079 5 0.54888229744311723 9 0.044510565034887713 
		36 0.085664144371984233
		4 4 0.24943922088385789 5 0.59266041826217741 9 0.050232700255025922 
		36 0.10766766059893876
		4 4 0.19415580025547446 5 0.63381398668608047 9 0.067444876841379356 
		36 0.1045853362170657
		4 4 0.17341879462425247 5 0.63083847022007888 9 0.051041429330743869 
		36 0.1447013058249248
		4 4 0.1105821281671524 5 0.60170900821685791 6 0.095597773790359497 
		36 0.19211108982563019
		4 4 0.12970169081839458 5 0.66874189181241239 9 0.069352255304936397 
		36 0.1322041620642567
		4 4 0.12999160878341515 5 0.65366597444562557 9 0.11630426607215999 
		36 0.10003815069879929
		4 4 0.080552376806735992 5 0.68780040740966797 9 0.093278400599956512 
		36 0.13836881518363953
		4 4 0.034287020819537495 5 0.69237810889168161 6 0.16850538677353699 
		36 0.10482948351524385
		4 4 0.042526893317699432 5 0.66788738965988159 6 0.18170443177223206 
		9 0.10788128525018692
		4 4 0.080918593386145085 5 0.67426566762628404 9 0.13377584217989796 
		36 0.1110398968076729
		1 4 0.067032881580538162;
	setAttr ".wl[889:1022].w"
		3 5 0.62458229530291487 6 0.15074387305039072 9 0.1576409500661563
		4 4 0.036942091527247645 5 0.62229342427651257 6 0.25757229807921311 
		9 0.083192186117026695
		4 4 0.060730907839794054 5 0.57822537206774438 6 0.23448538692859788 
		9 0.12655833316386367
		4 4 0.10255588591098785 5 0.58207064867019653 6 0.12306401133537292 
		9 0.19230945408344269
		4 4 0.11525138955001407 5 0.64275579207936395 9 0.16256960863091927 
		36 0.079423209739702724
		4 4 0.13368429343167165 5 0.6533302713433673 9 0.13733120364942553 
		36 0.075654231575535469
		4 4 0.20720225881341486 5 0.61397726258601637 9 0.1027695104892479 
		36 0.076050968111320852
		4 4 0.38008697334336777 5 0.50199131194163571 9 0.030365452845255825 
		36 0.087556261869740679
		4 4 0.36502632090792447 5 0.51897459642244959 9 0.038727398528970051 
		36 0.077271684140655952
		4 4 0.41364156641270711 5 0.5032425454845495 9 0.00332646672778412 
		36 0.079789421374959299
		4 4 0.34372473019156402 5 0.53162432113009928 9 0.044876784420585514 
		36 0.079774164257751135
		4 4 0.40845350220371984 5 0.50504309914973033 9 0.003128099548544796 
		36 0.083375299098005007
		4 4 0.37409019400535115 5 0.53189897438157541 9 0.011352712267352804 
		36 0.082658119345720635
		4 4 0.41385519832164902 5 0.48682383088208975 9 0.0038757915915401918 
		36 0.095445179204721023
		4 3 0.051972228840096932 4 0.32600900409367306 5 0.49423971588075266 
		9 0.12777905118547733
		4 3 0.021713587658769306 4 0.31589226855698815 5 0.53374533055831508 
		9 0.1286488132259275
		4 3 0.017044328026143252 4 0.29103532216671613 5 0.54612040112822957 
		9 0.14579994867891111
		4 4 0.26279088658995264 5 0.56331729469211922 9 0.13046464226793764 
		36 0.043427176449990446
		4 3 0.0055390251232969798 4 0.27666133358769618 5 0.57831692103158117 
		9 0.13948272025742575
		4 4 0.2483710879884749 5 0.58013276733111829 9 0.13861295219402511 
		36 0.032883192486381725
		4 4 0.27800411814463488 5 0.567696647873421 9 0.13089189323460737 
		36 0.023407340747336768
		4 4 0.25821316194122068 5 0.56974136723253632 9 0.14659342142456505 
		36 0.025452049401678053
		4 4 0.29726100521648313 5 0.53968108705582263 9 0.14277866748680673 
		10 0.020279240240887557
		4 4 0.26732280402275688 5 0.53392844497159864 9 0.17418172663518128 
		10 0.024567024370463156
		4 4 0.29710841510938574 5 0.49280536725527085 9 0.1736476738786065 
		10 0.036438543756736934
		4 4 0.25217059348587167 5 0.47127488431064368 9 0.22612345302895998 
		10 0.050431069174524654
		4 4 0.26770428221977177 5 0.42041657001400845 9 0.23648432249552492 
		10 0.075394825270694868
		4 4 0.2068513051185854 5 0.35580987003303965 9 0.32251468541111561 
		10 0.11482413943725928
		4 4 0.20573739400897334 5 0.29245441716232273 9 0.33585106826050476 
		10 0.16595712056819914
		4 4 0.12568856775760651 5 0.18260471522808075 9 0.44991225004196167 
		10 0.24179446697235107
		4 4 0.10325779919710457 5 0.09512474529631057 9 0.43772030528963068 
		10 0.36389715021695418
		4 4 0.040421150624752045 5 0.047333486378192902 9 0.47837033867835999 
		10 0.43387502431869507
		4 5 0.010360876252664271 9 0.48471809155818957 10 0.47917906163899693 
		34 0.025741970550149242
		4 4 0.083588921467836072 5 0.0212863350803368 9 0.4635843388391771 
		10 0.43154040461265003
		4 4 0.19177538442276992 5 0.20321965520411217 9 0.36583504625909097 
		10 0.23916991411402694
		4 5 0.0027924009706866803 9 0.43572136201786926 10 0.46982529157763558 
		34 0.091660945433808497
		4 5 0.0013122758858657346 9 0.46921491732172416 10 0.47238880505875874 
		34 0.057084001733651392
		3 9 0.32574960589408875 10 0.49053177237510681 34 0.18371862173080444
		3 9 0.37842374476159002 10 0.48989089593453861 34 0.1316853593038714
		3 9 0.47768368071397482 10 0.47768368071397482 34 0.044632638572050368
		4 5 0.0033417257735909437 9 0.48807507446547344 10 0.48807507446547344 
		34 0.02050812529546223
		4 5 0.018493935672498522 9 0.48694590278281918 10 0.47284657291524007 
		34 0.021713588629442327
		4 5 0.0073548484531740631 9 0.48946365053092789 10 0.48226138298139903 
		34 0.020920118034499034
		4 4 0.0051880673228747367 5 0.023636225060647702 9 0.52961014468199241 
		10 0.44156556293448518
		3 5 0.016525520288813267 9 0.52744335820337795 10 0.45603112150780872
		4 5 0.008697642985254727 6 0.061219197051689017 9 0.53948271525782865 
		10 0.39060044470522759
		3 5 0.019913023226449136 9 0.52761119309284987 10 0.45247578368070096
		4 5 0.0064393073138700255 9 0.48465705482122784 10 0.48101014458818997 
		34 0.027893493276712172
		4 5 0.0053406577048782169 9 0.4885175862837578 10 0.48470282938328951 
		34 0.021438926628074492
		3 9 0.48909742824410379 10 0.48909742824410379 34 0.021805143511792396
		4 5 0.0011444266433180621 9 0.49028763232087674 10 0.49028763232087674 
		34 0.018280308714928466
		3 9 0.47684443352255546 10 0.47684443352255546 34 0.046311132954889034
		3 9 0.40582895278930664 10 0.48082703351974487 34 0.11334401369094849
		3 9 0.3958648145198822 10 0.47100022435188293 34 0.13313496112823486
		3 9 0.47202258422928706 10 0.47200732544050877 34 0.055970090330204177
		3 9 0.39177539360857916 10 0.45638208901312816 34 0.15184251737829271
		3 9 0.38315404032400313 10 0.44594491192616392 34 0.17090104774983297
		3 9 0.46396581935984432 10 0.46395056057123657 34 0.072083620068919066
		3 9 0.48358892313564739 10 0.48358892313564739 34 0.032822153728705186
		3 9 0.45371175488400095 10 0.45371175488400095 34 0.092576490231998113
		3 9 0.3802243173122406 10 0.43050277233123779 34 0.18927291035652161
		3 9 0.37734034657478333 10 0.42111849784851074 34 0.20154115557670593
		3 9 0.44397650161333013 10 0.44397650161333013 34 0.11204699677333974
		4 5 0.0014038300207063091 9 0.47473868948751452 10 0.47473868948751452 
		34 0.049118791004264688
		4 5 0.0021057450163510048 9 0.46466773640208942 10 0.46466773640208942 
		34 0.068558782179470215
		3 9 0.4344853888298687 10 0.43447013004035145 34 0.13104448112977984
		3 9 0.37589074301394054 10 0.41272602715271794 34 0.21138322983334154
		3 9 0.37419700064961608 10 0.40238040086060167 34 0.22342259848978224
		3 9 0.42085908117470389 10 0.42085908117470389 34 0.15828183765059226
		4 5 0.0028839551183314298 9 0.45334553412463979 10 0.45270466498834189 
		34 0.091065845768686954
		4 5 0.0045319296570115733 9 0.44505988784729694 10 0.43297474830408317 
		34 0.1174334341916083
		4 5 0.0014801251122625245 9 0.4038605360948952 10 0.4021362631417586 
		34 0.19252307565108373
		4 5 0.011856259579385936 9 0.43701838714412322 10 0.40543221747709446 
		34 0.14569313579939636
		4 5 0.038361180430795325 9 0.4232852741208476 10 0.36926832657579955 
		34 0.16908521887255751
		4 5 0.055161364376544952 9 0.45809110999107361 10 0.37584495544433594 
		34 0.1109025701880455
		4 5 0.029282063900278446 9 0.46955062008389725 10 0.40906385501616871 
		34 0.092103460999655593
		3 5 0.099046310058691134 9 0.51450370592243133 10 0.38644998401887748
		3 5 0.07618829607963562 9 0.51523613929748535 10 0.40857556462287903
		3 5 0.11241321098188742 9 0.52553599289751063 10 0.36205079612060193
		3 5 0.14628824591636658 9 0.51953917741775513 10 0.3341725766658783
		4 4 0.0023651483433254762 5 0.13182268757469381 9 0.50713359235107036 
		10 0.35867857173091033
		4 4 0.0068818192027763356 5 0.1819790925175756 9 0.50424963940283707 
		10 0.30688944887681097
		4 4 0.02059967967607618 5 0.18547340916607402 9 0.47782101426201101 
		10 0.31610589689583879
		4 4 0.046555277133566428 5 0.22804609026031974 9 0.4590829329903533 
		10 0.26631569961576051
		4 4 0.010543984233334851 5 0.21283283572008194 9 0.51129930592431594 
		10 0.26532387412226727
		4 4 0.0011139085792667869 5 0.17364766898651612 9 0.53910123385619602 
		10 0.28613718857802106
		4 4 0.060105285195143104 5 0.2550698163717281 9 0.46039520665119871 
		10 0.22442969178193006
		3 4 0.18084992198869701 5 0.28932630584647795 9 0.52982377216482501
		4 4 0.10087739601077589 5 0.24650949056066951 9 0.40726330572915603 
		10 0.24534980769939863
		4 3 0.0041809721058017882 4 0.2624856896869433 5 0.31250477637525775 
		9 0.42082856183199718
		4 3 0.0017242695313344112 4 0.27614251698562409 5 0.32860304019186526 
		9 0.39353017329117629
		3 4 0.19894713163375854 5 0.30907148122787476 9 0.4919813871383667
		3 4 0.27348744869232178 5 0.33803310990333557 9 0.38847944140434265
		4 3 0.0030212863756424306 4 0.32289615709520342 5 0.35114062306614502 
		9 0.32294193346300909
		4 3 0.0067139697455348962 4 0.33044937806957292 5 0.34586099369963436 
		9 0.31697565848525788
		4 3 0.0097352564334869385 4 0.36206606030464172 5 0.3646906316280365 
		9 0.26350805163383484
		4 3 0.0045471886152071463 4 0.34822613698138105 5 0.36707103987413214 
		9 0.28015563452927966
		4 3 0.0015716792173024827 4 0.31154345718934756 5 0.35570304732829938 
		9 0.33118181626505055
		4 3 0.0023956664924442263 4 0.33440146620984773 5 0.36955825346202287 
		9 0.29364461383568513
		4 3 0.0057831695357180848 4 0.36324101720307117 5 0.37759974634051302 
		9 0.25337606692069775
		4 3 0.012191958816289594 4 0.37956816240823399 5 0.37642482203561678 
		9 0.23181505673985969
		4 3 0.013107499953589868 4 0.38710611806275058 5 0.38194858778860408 
		9 0.21783779419505545
		4 3 0.0062561989383163926 4 0.37045854105802206 5 0.38274204499290948 
		9 0.24054321501075207
		4 3 0.012100404241126071 4 0.38371861338353358 5 0.38092622515676755 
		36 0.22325475721857285
		4 3 0.022339208093172327 4 0.40172427967511926 5 0.37531089852621946 
		36 0.20062561370548906
		4 3 0.017944610180854671 4 0.38554970363554758 5 0.36977187694429309 
		36 0.22673380923930467
		4 3 0.0284275575432032 4 0.4041962257814295 5 0.35852598542955916 
		36 0.20885023124580815
		4 3 0.012451361725650411 4 0.35754939514157108 5 0.3566338678080529 
		36 0.27336537532472566
		4 3 0.0065156025144535792 4 0.34818035007455961 5 0.36047914254919572 
		36 0.28482490486179113
		4 3 0.0095826657756678743 4 0.37094682558704212 5 0.37372395500649874 
		36 0.24574655363079129
		4 3 0.0029449912685748304 4 0.3354696084592923 5 0.36597237527749027 
		36 0.29561302499464259
		4 3 0.0016327153992081514 4 0.30341039160456235 5 0.35246814520045966 
		36 0.34248874779576982
		3 4 0.29170671105384827 5 0.36298161745071411 36 0.34531167149543762
		4 3 0.0015411612208959071 4 0.3230334838670455 5 0.37245747681156544 
		36 0.30296787810049314
		4 3 0.0044708936079652147 4 0.35576408786721636 5 0.37624171043346055 
		36 0.26352330809135788
		4 3 0.002365148449055849 4 0.34221408575857587 5 0.37953765092727326 
		36 0.27588311486509504
		4 3 0.0057373921570149341 4 0.36752879140395384 5 0.38204013803176412 
		36 0.24469367840726719
		4 3 0.0030670634397977239 4 0.35310903643746788 5 0.38327610983517629 
		36 0.26054779028755809
		4 3 0.0033417258233865385 4 0.35544365950660206 5 0.38323033186130279 
		9 0.25798428280870861
		4 3 0.0030823224611686109 4 0.34848553380421798 5 0.37869841336498838 
		9 0.269733730369625
		3 4 0.23076218366622925 5 0.34627297520637512 36 0.42296484112739563
		3 4 0.24727245043624119 5 0.33475241563845298 36 0.41797513392530583
		4 3 0.0037842374365483177 4 0.31012436805316129 5 0.34142062131580081 
		36 0.34467077319448958
		4 3 0.0019684138530888765 4 0.23538567471068761 5 0.31078049996382823 
		36 0.45186541147239528
		4 3 0.0076142521787833017 4 0.30913251724783103 5 0.33205157611160979 
		36 0.35120165446177587
		4 3 0.0043488215716053994 4 0.21072710041218806 5 0.2838025455858208 
		36 0.50112153243038571
		4 3 0.013519493888168584 4 0.30203709062568301 5 0.3050888782461898 
		36 0.3793545372399586
		4 4 0.13835355433294841 5 0.21730373475993076 36 0.38350498104833097 
		37 0.26083772985878989
		4 4 0.056305792392439366 5 0.21301594455918649 36 0.44750133323483665 
		37 0.28317692981353748
		4 4 0.031265735160324944 5 0.15182725858945759 36 0.47202258598770819 
		37 0.34488442026250926
		4 4 0.0085603109535540168 5 0.15474173253690751 36 0.4976577405148252 
		37 0.33904021599471329
		4 4 0.0037994963726598824 5 0.099183639318835018 36 0.50312047154230022 
		37 0.39389639276620492
		3 5 0.10345616936683655 36 0.51612114906311035 37 0.3804226815700531
		2 5 0.043442434915267898 36 0.47016098394750083;
	setAttr ".wl[1022:1150].w"
		2 37 0.39598687893171791 61 0.090409702205513379
		3 5 0.066376745700836182 36 0.52016478776931763 37 0.41345846652984619
		4 5 0.020630197099982643 36 0.47768368160372998 37 0.43096055536998956 
		61 0.070725565926297834
		3 5 0.033829252788842627 36 0.52996110323860013 37 0.43620964397255729
		4 5 0.010421912117904625 36 0.48480963390910303 37 0.45413902105859189 
		61 0.050629432914400446
		4 5 0.0032501716231324021 36 0.46259250666075319 37 0.45261310972541224 
		61 0.081544211990702151
		4 5 0.0090180820037036764 36 0.45664148672220323 37 0.42510109348034314 
		61 0.10923933779374999
		4 5 0.0014343480693101496 36 0.43738460887015718 37 0.43193713172475401 
		61 0.12924391133577864
		3 36 0.45433737812182207 37 0.45433737812182207 61 0.091325243756355853
		4 5 0.0015716792465772893 36 0.47203784928264325 37 0.47098496304064658 
		61 0.055405508430132949
		3 36 0.46848249086378146 37 0.46848249086378146 61 0.063035018272437016
		4 5 0.0051728087075994314 36 0.42612344463109775 37 0.40462348279623156 
		61 0.16408026386507127
		4 5 0.026855879132208507 36 0.44621957345797658 37 0.39073778072158505 
		61 0.13618676668822988
		4 5 0.047364003603428573 36 0.43221178328833143 37 0.3564660224581806 
		61 0.16395819065005934
		4 5 0.011642634121631067 36 0.41080338413236434 37 0.37302205557131668 
		61 0.20453192617468791
		4 5 0.040268558858824674 36 0.38814374659901951 37 0.34012359254016133 
		61 0.23146410200199447
		4 4 0.14210727599103337 5 0.10041962414354647 36 0.42616921028242694 
		37 0.33130388958299323
		4 4 0.24432745211828572 5 0.13784999940022827 36 0.33716335390264757 
		37 0.28065919457883842
		4 3 0.019867246563472388 4 0.33742275142734823 5 0.2330205243765828 
		36 0.40968947763259661
		4 3 0.034302282439502285 4 0.41235979623422409 5 0.26878767704986639 
		36 0.28455024427640729
		4 3 0.028122377174391918 4 0.38875410684857714 5 0.31699091786501776 
		36 0.26613259811201317
		4 3 0.044373236927190696 4 0.44922560788114074 5 0.31653315064708254 
		36 0.18986800454458597
		4 3 0.038254368907755729 4 0.42879378635885645 5 0.33862820141528471 
		36 0.19432364331810309
		4 3 0.054184786571675636 4 0.48311587808194856 5 0.31950866938003397 
		36 0.14319066596634189
		4 3 0.046692606235640519 4 0.45912870935771133 5 0.33757534748902673 
		36 0.15660333691762141
		4 3 0.020325017827981851 4 0.36682688711623063 5 0.34604408885853621 
		36 0.26680400619725131
		4 3 0.035095751285552979 4 0.42734417319297791 5 0.36017394065856934 
		36 0.17738613486289978
		4 3 0.050080109947325029 4 0.46926069784083263 5 0.33374533430202308 
		9 0.1469138579098194
		4 3 0.058869304024339708 4 0.49523155220939241 5 0.31549554005466451 
		9 0.13040360371160345
		4 3 0.046845198375660153 4 0.45404744824837817 5 0.33226520318188074 
		9 0.16684215019408091
		4 3 0.035294119137174937 4 0.42267489275829906 5 0.3547264920371529 
		9 0.18730449606737309
		4 3 0.028900588092769987 4 0.39641413314126878 5 0.34602883651496191 
		9 0.22865644225099929
		4 3 0.018204012716151654 4 0.37639429814746328 5 0.35953306816953173 
		9 0.24586862096685339
		4 3 0.012863355844489882 4 0.34004730397892646 5 0.33792630247123717 
		9 0.30916303770534648
		4 3 0.0084382385440114702 4 0.26865034244645908 5 0.28825818364802402 
		9 0.43465323536150541
		4 3 0.021087968839824025 4 0.35855651102153496 5 0.31505301770783783 
		9 0.30530250243080315
		4 3 0.01470969709129101 4 0.30099946232419511 5 0.22159151712284283 
		9 0.46269932346167109
		4 3 0.030914778062597539 4 0.37727931352674576 5 0.27161058935305432 
		9 0.32019531905760235
		4 3 0.039139389991760254 4 0.42116427421569824 5 0.32466620206832886 
		9 0.21503013372421265
		4 3 0.045914396643638611 4 0.43471428751945496 5 0.30931562185287476 
		9 0.21005569398403168
		4 3 0.054291598094317328 4 0.47714960219599611 5 0.31558710101554466 
		9 0.15297169869414196
		4 3 0.038941025733947754 4 0.36321049928665161 5 0.25015640258789062 
		9 0.34769207239151001
		4 4 0.20047302245388893 5 0.11543449587472535 9 0.37235065739824386 
		10 0.31174182427314184
		4 5 0.088456548091347897 9 0.3260395204570925 10 0.31644159319667819 
		34 0.26906233825488135
		4 5 0.028259709056322142 9 0.38121613292074008 10 0.35060655548264746 
		34 0.23991760254029032
		4 4 0.11955443769693375 5 0.091264210641384125 9 0.43692684173583984 
		10 0.35225450992584229
		4 4 0.018768597184472564 5 0.12260623884268583 9 0.48625924639859147 
		10 0.37236591757425014
		4 4 0.097047381826098122 5 0.19159227752381769 9 0.41788357807609122 
		10 0.29347676257399291
		4 5 0.0069733732217611439 9 0.39085984139037355 10 0.37882047803415808 
		34 0.22334630735370725
		4 5 0.0022430762083692365 9 0.34314489212824195 10 0.37721827459355184 
		34 0.27739375706983699
		4 5 0.016784925201366752 9 0.33870450040740335 10 0.35748836797649081 
		34 0.28702220641473913
		3 9 0.36040284692640828 10 0.39029526128924996 34 0.24930189178434176
		4 3 0.022491797804832458 4 0.3973143994808197 5 0.37033647298812866 
		9 0.20985732972621918
		4 3 0.037720304685091688 4 0.43419546697652839 5 0.35822079252862915 
		9 0.16986343580975077
		4 3 0.024109255612303523 4 0.40604257734880811 5 0.37526512285793245 
		9 0.1945830441809559
		4 5 0.030502784656329624 6 0.097154191540693588 36 0.51453422925024228 
		37 0.35780879455273457
		3 5 0.084565499825004484 36 0.54491491343635867 37 0.37051958673863677
		4 5 0.033112077918288768 6 0.17402913647803259 36 0.50267796210414284 
		37 0.29018082349953583
		4 5 0.088349737885219881 6 0.1613794130189673 36 0.47811094282650157 
		37 0.27215990626931119
		4 4 0.0049286643731686897 5 0.17923248064563349 36 0.53241778163822995 
		37 0.28342107334296784
		4 4 0.0031128405038890676 5 0.22298008473472772 6 0.26535439812541678 
		36 0.50855267663596648
		4 4 0.033676661300088007 5 0.24049743830787063 36 0.48555734391840288 
		37 0.24026855647363843
		4 4 0.016311895163029042 5 0.19664301051438976 36 0.49730679578075854 
		37 0.28973829854182265
		4 4 0.083405816929172358 5 0.25252155033919699 36 0.43057907590074262 
		37 0.23349355683088802
		3 4 0.14036774635314941 5 0.29675745964050293 36 0.56287479400634766
		4 4 0.023132678552208068 5 0.26816204689744949 6 0.2449378267850322 
		36 0.46376744776531026
		4 4 0.096925310068388948 5 0.30861371525664838 6 0.21548791069173878 
		36 0.37897306398322383
		4 4 0.0018463416520795766 5 0.14489966654551628 36 0.52326238240647049 
		37 0.32999160939593364
		3 5 0.14666971564292908 6 0.29559776186943054 36 0.55773252248764038
		4 5 0.064881361537565574 6 0.26402684849480651 7 0.22623026202447516 
		36 0.4448615279431527
		3 5 0.12385748142216382 9 0.55077438725867289 10 0.32536813131916326
		4 5 0.05323872596236931 6 0.13615624302276425 9 0.50199132035692062 
		10 0.30861371065794579
		3 5 0.067643246032821097 9 0.54242770651516969 10 0.38992904745200918
		4 5 0.013214313314362597 6 0.1162737449198368 9 0.53783475901883759 
		10 0.33267718274696295
		4 5 0.023498894427913294 6 0.08268863630771045 9 0.52230107297840456 
		10 0.37151139628597168
		3 5 0.054184785764259419 9 0.51827268634127033 10 0.42754252789447023
		3 5 0.031158923226784346 9 0.52481879465639503 10 0.44402228211682065
		4 5 0.008758679358611977 6 0.064850846858726691 9 0.54071869480307011 
		10 0.38567177897959126
		4 5 0.0095063706951891876 9 0.47954528630626786 10 0.47045089918280208 
		34 0.040497443815740872
		4 5 0.014953841719890937 9 0.4749370599387252 10 0.45392537920231207 
		34 0.056183719139071803
		4 5 0.020492866635322571 9 0.47263294458389282 10 0.43367666006088257 
		34 0.073197528719902039
		4 5 0.0040588999350904932 6 0.10165560524802689 9 0.55199511375637345 
		10 0.34229038106050924
		4 5 0.013122759133641589 6 0.13986419466939276 9 0.52390326289234834 
		10 0.32310978330461737
		4 5 0.031952391238616699 6 0.085435260948101624 9 0.5376363812434396 
		10 0.34497596656984203
		4 5 0.068787672138122258 6 0.25043106265687243 9 0.44750133490190913 
		10 0.23327993030309624
		4 5 0.13339437345572749 6 0.16804760444093339 9 0.44855421113142058 
		10 0.25000381097191854
		4 4 0.021728846771105252 5 0.21788356792398603 6 0.38432898401601268 
		9 0.37605860128889601
		4 4 0.069443807005882263 5 0.19441519677639008 9 0.49996185302734375 
		10 0.23617914319038391
		4 4 0.062378884756093128 5 0.11195544403691837 9 0.51274890853648425 
		10 0.31291676267050422
		4 4 0.13229571085727646 5 0.27463188358199769 9 0.42139314977238851 
		10 0.17167925578833734
		4 4 0.19555962231427149 5 0.43219653093961274 9 0.29465171914288191 
		10 0.077592127603233807
		4 4 0.023605706565922795 5 0.057282370544115703 9 0.52510870383303299 
		10 0.39400321905692848
		4 4 0.27124437285595576 5 0.36304264719720708 9 0.24676890303538884 
		10 0.11894407691144829
		4 4 0.32613107319078538 5 0.44702830577620634 9 0.17355611791047365 
		10 0.053284503122534577
		4 4 0.2304112272260482 5 0.51830320584954315 6 0.035492482865369268 
		9 0.21579308405903944
		4 4 0.34045929097152455 5 0.49465171055479024 9 0.13638514432741491 
		10 0.028503854146270314
		4 4 0.23138780504001258 5 0.56876479625909937 9 0.16942091002168472 
		36 0.030426488679203393
		4 4 0.3219348406287138 5 0.53363852301437531 9 0.1251697507642647 
		10 0.019256885592646156
		4 4 0.2198977684944203 5 0.59555961476444053 9 0.14927901772496158 
		36 0.035263599016177628
		4 3 0.004745555838294729 4 0.30373083243927146 5 0.56066224557304445 
		9 0.13086136614938934
		4 4 0.22915999847456811 5 0.58699930370225728 9 0.13875028646085732 
		36 0.045090411362317333
		4 3 0.013611047541360416 4 0.28479439046680405 5 0.56322574667933001 
		9 0.13836881531250553
		4 4 0.2800793401911732 5 0.55548943123760508 9 0.11255055130553528 
		36 0.051880677265686494
		4 3 0.041611349522644669 4 0.29396506048869114 5 0.5141222285433773 
		9 0.15030136144528683
		4 3 0.12472724076563685 4 0.31747922064751966 5 0.42560463826652895 
		9 0.13218890032031461
		4 3 0.18739604949951172 4 0.3649958074092865 5 0.40270084142684937 
		9 0.044907301664352417
		4 3 0.32558174951130897 4 0.3295033177881444 5 0.30580606145244654 
		9 0.039108871248100065
		4 3 0.12037842900124832 4 0.41841763881471217 5 0.3934080957384124 
		36 0.067795836445627158
		4 3 0.053406577756280368 4 0.41673913753308034 5 0.45879301599708577 
		36 0.071061268713553505
		4 4 0.25003433600119257 5 0.23382924845560266 10 0.25870144752713214 
		34 0.25743496801607263
		4 4 0.30167085381851871 5 0.32030213356468279 10 0.18919661923045844 
		34 0.18883039338634006
		4 4 0.38968490683246615 5 0.35469596785241436 10 0.13121232097121355 
		34 0.12440680434390594
		4 4 0.35695430104502585 5 0.36491950802624967 10 0.1391775438312062 
		34 0.13894864709751834
		4 4 0.31931028721661231 5 0.33832303697833538 10 0.17880522247568437 
		34 0.16356145332936803
		4 4 0.27443352341651917 5 0.27824825048446655 10 0.23593500256538391 
		34 0.21138322353363037
		4 4 0.30247959494590759 5 0.30559241771697998 10 0.22526894509792328 
		34 0.16665904223918915
		4 4 0.34348058700561523 5 0.34247347712516785 10 0.17763027548789978 
		34 0.13641566038131714
		4 4 0.36314945871905296 5 0.36458381467187689 10 0.14168001500248886 
		34 0.13058671160658133
		4 4 0.38385596013391104 5 0.40595101402809441 10 0.10528725150330548 
		34 0.10490577433468906
		4 4 0.40834667974452166 5 0.41332113434880136 9 0.093217364749183018 
		10 0.085114821157494025
		4 4 0.39745173450487459 5 0.43956664859602823 9 0.10034333318983515 
		10 0.062638283709262069
		4 4 0.37468529166302039 5 0.45409322292461868 9 0.11720454823826866 
		10 0.054016937174092276
		4 4 0.32623788228276546 5 0.31743344191560979 10 0.20050354003155918 
		35 0.15582513577006554
		4 4 0.3497367851396917 5 0.31921872972277893 10 0.17027542248778674 
		35 0.16076906264974269
		4 3 0.067887389687166871 4 0.3639734468752171 5 0.4342259861728397 
		9 0.13391317726477631
		4 3 0.14822613972088486 4 0.34122225133743506 5 0.38065155773384041 
		9 0.12990005120783968
		4 3 0.3814602792263031 4 0.26271459460258484 5 0.27782100439071655 
		9 0.078004121780395508
		4 3 0.63067061648772094 4 0.12286564890840126 5 0.14114596159973683 
		9 0.10531777300414105
		2 2 0.022674906492049101 3 0.87727169221777423;
	setAttr ".wl[1150:1173].w"
		2 4 0.063675893910022957 5 0.036377507380153822
		4 3 0.156725404311338 4 0.38803693073932932 5 0.31157397759595545 
		10 0.14366368735337723
		4 3 0.25806057837695745 4 0.35393301179905251 5 0.26982528373338704 
		10 0.11818112609060297
		4 3 0.41109329462051392 4 0.2843824028968811 5 0.20773632824420929 
		10 0.096787974238395691
		4 3 0.59649042497603821 4 0.20486762509144471 5 0.12660410622942131 
		10 0.072037843703095808
		4 3 0.80430304554680521 4 0.12364385207941465 5 0.023270008955504694 
		10 0.048783093418275414
		3 3 0.93014419598585474 4 0.043091479929675235 11 0.026764324084469996
		3 3 0.97648584660797222 10 0.011764706090530928 11 0.01174944730149685
		3 3 0.99163805607264632 10 0.0041809719636768591 11 0.0041809719636768591
		3 3 0.99765011057264896 10 0.0011749447136755011 11 0.0011749447136755011
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1
		1 3 1;
	setAttr -s 79 ".pm";
	setAttr ".pm[0]" -type "matrix" 0 -0 -1 -0 0.99799027986901856 -0.063367194090933054 -0 0
		 -0.063367194090933054 -0.99799027986901867 -0 0 -95.559524140488392 8.3529922361861715 -3.4314998759166221e-17 1;
	setAttr ".pm[1]" -type "matrix" 0 -0 -1 -0 0.98220797016103401 0.18779644126591369 -0 -0
		 0.18779644126591374 -0.98220797016103401 0 -0 -98.179537472967525 -16.686798167121658 4.3202194641745812e-16 1;
	setAttr ".pm[2]" -type "matrix" 0 -0 -1 -0 0.99176140629857179 0.12809884065314414 -0 -0
		 0.1280988406531442 -0.99176140629857179 0 -0 -105.79112581470955 -10.312733827340182 2.4642770704620008e-16 1;
	setAttr ".pm[3]" -type "matrix" 0 -0 -1 -0 0.99804167658749499 -0.062552472328609804 -0 0
		 -0.062552472328609748 -0.99804167658749499 0 0 -112.93116808215187 11.337483986926584 1.2350709678255032e-16 1;
	setAttr ".pm[4]" -type "matrix" 0 -7.8457562571503513e-06 -0.99999999996922206 -0
		 0.98641974755132822 -0.16424396987138712 1.2886181543573101e-06 0 -0.16424396987644216 -0.98641974752096839 7.7392089065275019e-06 0
		 -119.65995581271704 23.693152323860112 -0.00018589069810239194 1;
	setAttr ".pm[5]" -type "matrix" -1.8369095133075878e-13 1.5897534116537124e-11 -1 -0
		 0.98439676970875678 -0.17596306370077874 -2.9782035882479106e-12 0 -0.17596306370077869 -0.984396769708757 -1.5617158413075801e-11 0
		 -138.80815577827528 25.345680206388408 4.2901809001282565e-10 1;
	setAttr ".pm[6]" -type "matrix" -6.6158600073637137e-12 1.4456684603152542e-11 -1 -0
		 0.97116051578906692 0.23842661884175731 -2.9782035882479102e-12 -0 0.23842661884175742 -0.97116051578906704 -1.5617158413075794e-11 -0
		 -148.02413413726134 -37.954183218738514 4.2901649057184837e-10 1;
	setAttr ".pm[7]" -type "matrix" -6.1294451675869628e-12 1.7098227304699728e-06 -0.99999999999853828 -0
		 0.97858030038111177 0.20586547963631138 3.5198747834748905e-07 -0 0.20586547963661239 -0.97858030037968147 -1.6732001030229328e-06 -0
		 -154.31633419745555 -32.819682332318422 -5.6114928351548255e-05 1;
	setAttr ".pm[8]" -type "matrix" 2.0731685376878032e-14 -5.2736972103718422e-13 -1 -0
		 0.99999999999999956 -2.7642915900707262e-08 2.0731699180479388e-14 0 -2.7642915845119117e-08 -0.99999999999999922 5.2736971586760892e-13 0
		 -162.57510095546689 0.6631271895736045 -6.9220508941227083e-11 1;
	setAttr ".pm[9]" -type "matrix" 0.98722325285369872 -0.045885930500282487 0.15259334981277803 -0
		 -0.15258975017460899 0.0036018072449419116 0.98828305415312145 0 -0.045897899370362635 -0.99894019258747058 -0.0034459348070639737 -0
		 20.834526686610335 -2.1993972353802893 -144.81073304490477 1;
	setAttr ".pm[10]" -type "matrix" 0.57603356970603825 -0.032592100671480384 0.81677602899787582 -0
		 -0.81709064454000069 -0.051578494511193576 0.57419729841681266 0 0.023413781773248543 -0.99813697150129566 -0.05634164485791858 -0
		 106.43028049579613 5.4729235446178173 -98.116150068235385 1;
	setAttr ".pm[11]" -type "matrix" 0.46829763500528526 0.33700777958812422 0.81677602899787605 -0
		 -0.60274413765566648 -0.55407307010227613 0.57419729841681277 0 0.64606255855774775 -0.76120220013116147 -0.056341644857918607 -0
		 57.705277019372737 53.733736277159572 -98.116150068235285 1;
	setAttr ".pm[12]" -type "matrix" 0.50409945495245101 0.33849062611899494 0.79454882514934999 -0
		 -0.60398945624054445 -0.51942160302091689 0.60448154236951968 0 0.61731716019149518 -0.78461792889581095 -0.057395377761239361 -0
		 47.473584484677097 49.768920692360659 -100.73462759546058 1;
	setAttr ".pm[13]" -type "matrix" 0.50409934937943979 0.33849062722902823 0.79454889165697262 -0
		 -0.6039895354012087 -0.51942160364797818 0.60448146273446202 0 0.61731716895049649 -0.78461792800181462 -0.057395295774846596 -0
		 38.39948766307743 50.089752883142609 -100.46807637246528 1;
	setAttr ".pm[14]" -type "matrix" 0.45776606561811328 -0.64550904437145162 0.61136593199422551 -0
		 -0.63486683690404511 -0.71872771411568359 -0.28350409584606834 0 0.62241009677540171 -0.25835740089399173 -0.73882144313449372 -0
		 34.684346122405991 109.9739843467096 12.011274326347484 1;
	setAttr ".pm[15]" -type "matrix" 0.48489773769626671 -0.67018644860059917 0.56189350244433245 -0
		 -0.60591821332048457 -0.72073617183479421 -0.33675286097587714 0 0.63066417588408663 -0.17717080662751039 -0.75556151472623567 -0
		 26.831433812930602 110.68854436359625 20.436040249929938 1;
	setAttr ".pm[16]" -type "matrix" 0.062225503872753163 -0.82486585489922115 0.56189350244433234 -0
		 -0.89359104695641289 -0.29680389388264899 -0.33675286097587698 0 0.44454811603146255 -0.48114838667242121 -0.75556151472623534 -0
		 75.618504547712334 83.448560433435006 20.436040249929921 1;
	setAttr ".pm[17]" -type "matrix" -0.23431932551154891 -0.79332852312434454 0.56189350244433212 0
		 -0.94077026842430067 0.03935495741872172 -0.33675286097587692 0 0.24504235499333674 -0.60752040436837662 -0.75556151472623523 -0
		 95.462679462783328 53.044054692818136 20.436040249929874 1;
	setAttr ".pm[18]" -type "matrix" -0.36851954040065693 -0.74058695657817897 0.56189350244433245 0
		 -0.91964393761217333 0.20212010943430922 -0.33675286097587703 0 0.13582480022464327 -0.6408419626620373 -0.75556151472623545 -0
		 100.78697591503283 36.09088162744461 20.436040249929874 1;
	setAttr ".pm[19]" -type "matrix" 0.50165929984922586 -0.86150484141863237 0.078405070544201108 -0
		 -0.81946977563034784 -0.50229885137241892 -0.27598034484052603 0 0.27714118009262162 0.074197520997709002 -0.95796006919634413 -0
		 53.495590922837458 93.883233434698852 39.527703497094578 1;
	setAttr ".pm[20]" -type "matrix" 0.26354050175138494 -0.93037057822145774 0.25486661436229341 -0
		 -0.91778928814692895 -0.32317414573818043 -0.23069740806768926 0 0.29700038131184336 -0.17311573789308352 -0.93905362721963481 -0
		 70.569005181413004 84.524479688125552 25.509234300609666 1;
	setAttr ".pm[21]" -type "matrix" -0.092201469831926147 -0.96257046383334111 0.25486661436229335 0
		 -0.97249693640637469 0.032068903802027635 -0.23069740806768926 0 0.21388921815053188 -0.26912764176985104 -0.93905362721963481 -0
		 92.884441063882775 54.52368272214644 25.509234300609606 1;
	setAttr ".pm[22]" -type "matrix" -0.17436652109979217 -0.95112529416636626 0.25486661436229341 0
		 -0.96616935149144256 0.1153060716070639 -0.23069740806768926 0 0.19003447202589024 -0.28647021598673789 -0.93905362721963481 -0
		 95.183488685287372 46.536522629255515 25.509234300609588 1;
	setAttr ".pm[23]" -type "matrix" 0.59060503118117336 -0.73083333884862656 0.34215249227625594 -0
		 -0.65963271076520436 -0.68147046384688714 -0.31699005314497958 0 0.46483371653961686 -0.03847905575344418 -0.8845614609716449 -0
		 29.859978948116556 107.22853509030105 30.39530525378953 1;
	setAttr ".pm[24]" -type "matrix" 0.1562381940841959 -0.88283473502988563 0.44293617749515585 -0
		 -0.90993079452509795 -0.30308700145347256 -0.28313286408480803 0 0.38420772491483385 -0.35880510054157982 -0.85067227763758335 -0
		 73.837837134590927 84.41352968000156 20.992614199752783 1;
	setAttr ".pm[25]" -type "matrix" -0.13914028536722983 -0.88569042201770753 0.44293617749515563 0
		 -0.95903783110600815 0.0090675124822773168 -0.28313286408480792 0 0.24675173656006633 -0.46418773848894085 -0.85067227763758302 -0
		 92.555475994070321 57.453831159040327 20.992614199752879 1;
	setAttr ".pm[26]" -type "matrix" -0.2784797358133736 -0.85220688767886221 0.44293617749515568 0
		 -0.94534178719106654 0.1617550205265135 -0.28313286408480798 0 0.16964062641865221 -0.49757284283527065 -0.85067227763758313 -0
		 98.291161330797465 42.333914954640612 20.992614199752715 1;
	setAttr ".pm[27]" -type "matrix" -0.23677732947120234 0.3580451068080544 0.90318336883453276 -0
		 -0.46744570505554672 -0.85693276787306782 0.21716524623089359 0 0.85172237793403516 -0.3707693795827951 0.37026889970693028 -0
		 43.319619360309311 78.534900135551482 -70.958618846610079 1;
	setAttr ".pm[28]" -type "matrix" -0.045744985004837348 0.47737462531297914 0.87750832671502355 -0
		 -0.75995290887963407 -0.58677024939719302 0.27959300904660833 0 0.6483663876484409 -0.65407502744688761 0.38962403139188329 -0
		 64.345843526109718 52.176126644376552 -76.528230690124133 1;
	setAttr ".pm[29]" -type "matrix" 0.037845217613481696 0.47806576540219692 0.87750832671502388 -0
		 -0.85029910087978788 -0.44589145353469845 0.2795930090466085 0 0.52493730915873293 -0.75672579949088858 0.38962403139188334 -0
		 69.389458175496756 40.745793878274462 -76.528230690124218 1;
	setAttr ".pm[30]" -type "matrix" 0.38282471691666747 -0.60140250132809647 0.70125620675611999 -0
		 -0.58595958989602781 -0.74492304281921062 -0.31896868072876322 0 0.71421046976822689 -0.28879870441758798 -0.63757251603262433 -0
		 27.99023961814401 111.53927736274952 11.729791100091541 1;
	setAttr ".pm[31]" -type "matrix" 0.1128251535879628 -0.70392486616390404 0.70125620675611988 -0
		 -0.83339914156516925 -0.4513367385363074 -0.31896868072876322 0 0.54103267512812081 -0.54843863033482421 -0.63757251603262433 -0
		 64.530787868163245 93.574290195810747 11.488915408916094 1;
	setAttr ".pm[32]" -type "matrix" -0.071878640933652316 -0.70927652820571274 0.70125620675612022 0
		 -0.9214016860641987 -0.22198629154117586 -0.31896868072876333 0 0.38190626323167609 -0.66906568653925647 -0.63757251603262455 -0
		 82.46950047678385 74.89477311445232 11.488915408916181 1;
	setAttr ".pm[33]" -type "matrix" -0.22388412434001725 -0.6768423977223369 0.70125620675611988 0
		 -0.94761232662415806 -0.017025250192036354 -0.31896868072876322 0 0.22783058903152723 -0.73593104942064824 -0.63757251603262433 -0
		 94.207329612463568 55.804497211239173 11.488915408916206 1;
	setAttr ".pm[34]" -type "matrix" 0.60649254765415761 -0.029307966917277328 0.79454882336779309 -0
		 -0.79463176670251312 -0.056235375135710391 0.60448154473944782 0 0.026965626030396646 -0.99798728732310105 -0.057395377464279113 -0
		 93.385259004106871 6.0267579735113301 -101.69680888390984 1;
	setAttr ".pm[35]" -type "matrix" 0.57603356970603792 -0.032592100671480384 0.81677602899787549 -0
		 -0.81709064454000024 -0.051578494511193569 0.57419729841681255 0 0.023413781773248536 -0.99813697150129577 -0.056341644857918552 -0
		 87.916189004096807 5.4729235446178093 -98.116150068235257 1;
	setAttr ".pm[36]" -type "matrix" 0.98722325285135626 -0.045885930531461817 0.15259334981855666 -0
		 0.15258975018048893 -0.0036018072452173393 -0.98828305415221207 0 0.04589789940119781 0.99894019258603728 0.0034459348118278778 -0
		 -20.834547706916286 2.1994343628065227 144.81067317362968 1;
	setAttr ".pm[37]" -type "matrix" 0.57603356970190278 -0.032592100702963533 0.81677602899953605 -0
		 0.81709064454343117 0.051578494510997296 -0.57419729841194778 0 -0.023413781755254815 0.99813697150027758 0.056341644883428618 -0
		 -106.42986716562406 -5.4728614336200669 98.115865171166732 1;
	setAttr ".pm[38]" -type "matrix" 0.46829763502187433 0.33700777956104855 0.81677602899953594 -0
		 0.60274413765845702 0.55407307010428153 -0.57419729841194778 0 -0.64606255854311956 0.76120220014168849 0.056341644883428604 -0
		 -57.705340251771261 -53.733707545047949 98.115865171166647 1;
	setAttr ".pm[39]" -type "matrix" 0.50409945496813513 0.33849062609139419 0.79454882515115732 -0
		 0.60398945624354849 0.51942160302293072 -0.60448154236478668 0 -0.61731716017574878 0.78461792890638449 0.057395377786054892 -0
		 -47.473684776586033 -49.768895097327757 100.73434494823337 1;
	setAttr ".pm[40]" -type "matrix" 0.50409934939512391 0.3384906272014277 0.79454889165878018 -0
		 0.60398953540421285 0.51942160364999235 -0.60448146272972936 0 -0.61731716893474997 0.78461792801238839 0.057395295799662009 -0
		 -38.399636541036216 -50.089725570257912 100.46779515240362 1;
	setAttr ".pm[41]" -type "matrix" 0.45776606563377215 -0.64550904438380219 0.61136593196945999 -0
		 0.63486683690677292 0.71872771411183767 0.28350409584970848 0 -0.62241009676110248 0.2583574008738313 0.73882144315358966 -0
		 -34.684463937345598 -109.97370532720171 -12.011352937634847 1;
	setAttr ".pm[42]" -type "matrix" 0.48489773771235584 -0.67018644861042576 0.56189350241872726 -0
		 0.60591821332337403 0.72073617183080185 0.3367528609792223 0 -0.63066417586893997 0.17717080660657952 0.7555615147437863 -0
		 -26.831578690188984 -110.68870264748128 -20.436071565158709 1;
	setAttr ".pm[43]" -type "matrix" 0.062225503881315924 -0.82486585491601716 0.56189350241872715 -0
		 0.8935910469567846 0.29680389387773493 0.33675286097922219 0 -0.44454811602951722 0.48114838664665804 0.75556151474378597 -0
		 -75.618512350651898 -83.448596053775717 -20.43607299554056 1;
	setAttr ".pm[44]" -type "matrix" -0.23431932550949855 -0.79332852314308511 0.56189350241872682 -0
		 0.94077026842290523 -0.039354957423448404 0.33675286097922208 -0 -0.24504235500065333 0.60752040434359766 0.75556151474378563 -0
		 -95.46267995502707 -53.044009781515676 -20.436035949871407 1;
	setAttr ".pm[45]" -type "matrix" -0.36851954040189222 -0.74058695659699125 0.56189350241872693 -0
		 0.91964393760997865 -0.20212010943872191 0.33675286097922214 -0 -0.13582480023615154 0.64084196263890547 0.75556151474378552 -0
		 -100.78693029527457 -36.090890550801703 -20.436070334886573 1;
	setAttr ".pm[46]" -type "matrix" 0.50165929985300117 -0.86150484141930661 0.078405070512635913 -0
		 0.81946977563333656 0.50229885136728747 0.27598034484099093 -0 -0.27714118007695088 -0.074197521024616214 0.95796006919879351 -0
		 -53.495341000175429 -93.883047175076555 -39.527588871886962 1;
	setAttr ".pm[47]" -type "matrix" 0.263540501755195 -0.93037057822878932 0.25486661433158864 -0
		 0.91778928814849914 0.32317414573263831 0.23069740806920488 0 -0.29700038130360962 0.1731157378640252 0.93905362722759544 -0
		 -70.569010513731598 -84.524426128280354 -25.509209034727803 1;
	setAttr ".pm[48]" -type "matrix" -0.092201469831037788 -0.96257046384155609 0.25486661433158864 -0
		 0.97249693640582635 -0.032068903807761735 0.23069740806920488 -0 -0.21388921815340942 0.26912764173978615 0.93905362722759544 -0
		 -92.884403844990771 -54.523672331339355 -25.50924166393435 1;
	setAttr ".pm[49]" -type "matrix" -0.17436652109961107 -0.9511252865790093 0.25486664267733117 -0
		 0.96616935149040428 -0.11530606473741112 0.23069741150559331 -0 -0.19003447203133403 0.28647024394300918 0.9390536186901165 -0
		 -95.183449448266927 -46.536498747224563 -25.50920927407406 1;
	setAttr ".pm[50]" -type "matrix" 0.59060503119176289 -0.73083333885388757 0.34215249224673927 -0
		 0.65963271076872321 0.68147046384253351 0.31699005314701545 0 -0.46483371652116828 0.038479055730619105 0.88456146098233213 -0
		 -29.860193634392186 -107.22872913461252 -30.39536124389673 1;
	setAttr ".pm[51]" -type "matrix" 0.15623819409077636 -0.882834735042898 0.44293617746689945 -0
		 0.90993079452602954 0.30308700144821332 0.28313286408744465 0 -0.38420772490995198 0.35880510051400616 0.85067227765141884 -0
		 -73.837860731263675 -84.413535990483211 -20.992655495034636 1;
	setAttr ".pm[52]" -type "matrix" -0.13914028536523573 -0.88569042203215176 0.44293617746689928 -0
		 0.95903783110518004 -0.0090675124875545798 0.28313286408744448 -0 -0.24675173656440971 0.46418773846127742 0.85067227765141828 -0
		 -92.5554300012748 -57.45383159268782 -20.992631883013306 1;
	setAttr ".pm[53]" -type "matrix" -0.27847973581370616 -0.85220688769344011 0.44293617746689934 -0
		 0.9453417871894082 -0.16175502053159121 0.28313286408744454 -0 -0.16964062642734801 0.49757284280865294 0.85067227765141851 -0
		 -98.291149148823592 -42.333968024759507 -20.992620661524899 1;
	setAttr ".pm[54]" -type "matrix" -0.23677732944738361 0.35804510679136936 0.90318336884739125 -0
		 0.46744570505413796 0.8569327678751999 -0.21716524622551273 0 -0.85172237794143002 0.37076937959398021 -0.37026889967872051 0
		 -43.319422238623893 -78.534515870392084 70.958506589554858 1;
	setAttr ".pm[55]" -type "matrix" -0.045744984989112718 0.47737462528905483 0.87750832672885848 -0
		 0.75995290887936295 0.58677024940003586 -0.27959300904138068 0 -0.64836638764986876 0.65407502746179957 -0.38962403136447582 0
		 -64.345839327249948 -52.176173230388699 76.528256968974361 1;
	setAttr ".pm[56]" -type "matrix" 0.037845217624813077 0.47806576537590528 0.87750832672885837 -0
		 0.8502991008800147 0.44589145353754467 -0.27959300904138062 0 -0.52493730915754944 0.75672579950582142 -0.38962403136447565 -0
		 -69.389506510419253 -40.745817579936116 76.528211143392554 1;
	setAttr ".pm[57]" -type "matrix" 0.3828247169354852 -0.60140250134155371 0.701256206734306 -0
		 0.58595958989830965 0.74492304281562771 0.31896868073293877 0 -0.71421046975626867 0.28879870439880556 0.63757251605452803 -0
		 -27.990338472714193 -111.53948953296096 -11.729855138796443 1;
	setAttr ".pm[58]" -type "matrix" 0.11282515359989771 -0.70392486618372185 0.70125620673430589 -0
		 0.83339914156584216 0.45133673853211298 0.31896868073293871 0 -0.54103267512459507 0.54843863031283846 0.63757251605452792 -0
		 -64.530772805029557 -93.574276600955798 -11.488903496402385 1;
	setAttr ".pm[59]" -type "matrix" -0.071878640927211676 -0.70927652822793241 0.701256206734306 -0
		 0.92140168606377171 0.22198629153694938 0.31896868073293877 -0 -0.38190626323391941 0.66906568651710341 0.63757251605452803 -0
		 -82.469548696630184 -74.894751438847649 -11.48893560306419 1;
	setAttr ".pm[60]" -type "matrix" -0.22388412433854513 -0.67684239774542387 0.70125620673430589 -0
		 0.94761232662282524 0.017025250188002872 0.31896868073293871 -0 -0.22783058903851836 0.73593104939950749 0.63757251605452792 -0
		 -94.207306090605428 -55.804520795970255 -11.488932042382215 1;
	setAttr ".pm[61]" -type "matrix" 0.60649254765026672 -0.029307966948783556 0.79454882336960109 -0
		 0.79463176670612568 0.056235375135533672 -0.60448154473471494 0 -0.026965626011451624 0.99798728732218578 0.057395377489094838 -0
		 -93.385000898837362 -6.0267045524860139 101.69661493443279 1;
	setAttr ".pm[62]" -type "matrix" 0.57603356970190256 -0.03259210070296354 0.81677602899953583 -0
		 0.81709064454343094 0.051578494510997296 -0.57419729841194755 0 -0.023413781755254808 0.99813697150027769 0.056341644883428611 -0
		 -87.916071312962941 -5.4728818388958604 98.116066736292908 1;
	setAttr ".pm[63]" -type "matrix" -0.054523910657437967 -0.1460129330800598 -0.98777900693423215 0
		 -0.99851165534365582 0.0092329884397982145 0.053751521535134128 0 0.0012717348352381784 0.98923959448549592 -0.14629903414814568 -0
		 92.857360147214592 -4.8418851905416949 -14.502292380266628 1;
	setAttr ".pm[64]" -type "matrix" -0.04157786421258719 -0.15021289780688596 -0.98777900693423215 0
		 -0.99551014080239097 -0.077912344928525334 0.053751521535134128 0 -0.085034350512737902 0.98557889173835123 -0.14629903414814568 -0
		 49.749714492727101 -0.50364160660815482 -14.502292380266638 1;
	setAttr ".pm[65]" -type "matrix" 0.0046495256007424747 -0.14803750047914044 -0.98897081876240234 -0
		 -0.99950197930304496 -0.031556184277057558 2.455947517528231e-05 0 -0.031211781124816953 0.98847817663606541 -0.14811049602663426 -0
		 8.26888862648679 -0.85203293990604712 -14.078251050540022 1;
	setAttr ".pm[66]" -type "matrix" 0.14803750047914047 0.0046495256007425059 -0.98897081876240245 -0
		 0.031556184277057787 -0.99950197930304485 2.4559475175282321e-05 0 -0.98847817663606563 -0.031211781124817164 -0.14811049602663426 0
		 16.089627544398237 1.2594520191259586 -13.539305435248426 1;
	setAttr ".pm[67]" -type "matrix" -0.044064310719183056 -0.14803750057573392 -0.98799961282590243 0
		 -0.99828778764580228 -0.031556185440510851 0.049251397926289034 0 -0.038468552846355836 0.98847817658445791 -0.14639352737800065 -0
		 35.680238710006385 -2.1603644829028301 -14.379575794759738 1;
	setAttr ".pm[68]" -type "matrix" -0.044064310719183056 -0.14803750057573392 -0.98799961282590243 0
		 -0.99828778764580228 -0.031556185440510851 0.049251397926289034 0 -0.038468552846355836 0.98847817658445791 -0.14639352737800065 -0
		 21.623113922100643 -1.5061940863598642 -14.480590844561741 1;
	setAttr ".pm[69]" -type "matrix" -0.04672652176680351 -0.14721887520437618 -0.98799961282742177 0
		 -0.99869449405102084 -0.013550178981221499 0.049251397967495926 0 -0.020638306998206981 0.98901111997445967 -0.14639352735388469 -0
		 78.564887298044155 -3.0517164512990425 -14.148382836895289 1;
	setAttr ".pm[70]" -type "matrix" -0.04672652176680351 -0.14721887520437618 -0.98799961282742177 0
		 -0.99869449405102084 -0.013550178981221499 0.049251397967495926 0 -0.020638306998206981 0.98901111997445967 -0.14639352735388469 -0
		 64.121707099473397 -3.3813227074594181 -14.213471789854614 1;
	setAttr ".pm[71]" -type "matrix" -0.05452391065743796 -0.14601293308005972 -0.98777900693423226 -0
		 0.99851165534365627 -0.0092329884397976958 -0.053751521535134204 0 -0.0012717348352376708 -0.98923959448549614 0.14629903414814557 0
		 -92.856783467811482 4.8325715231484505 14.50375024985332 1;
	setAttr ".pm[72]" -type "matrix" -0.04157786421258728 -0.15021289780688588 -0.98777900693423237 0
		 0.99551014080239142 0.077912344928525293 -0.053751521535134204 0 0.085034350512737819 -0.98557889173835178 0.14629903414814563 -0
		 -49.748281886075681 0.49441775222512119 14.503750249853315 1;
	setAttr ".pm[73]" -type "matrix" 0.0046495256007424313 -0.14803750047914024 -0.988970818762402 -0
		 0.99950197930304474 0.031556184277057427 -2.4559475175284022e-05 -0 0.031211781124816783 -0.98847817663606496 0.14811049602663415 -0
		 -8.2680003557588648 0.84275393938400234 14.079758090376085 1;
	setAttr ".pm[74]" -type "matrix" 0.1480375004791403 0.0046495256007424626 -0.98897081876240223 -0
		 -0.031556184277057656 0.99950197930304452 -2.4559475175284902e-05 0 0.98847817663606541 0.031211781124816994 0.14811049602663418 -0
		 -16.080342821830293 -1.2585637483980359 13.540870649217794 1;
	setAttr ".pm[75]" -type "matrix" -0.044064310719183056 -0.14803750057573375 -0.98799961282590198 0
		 0.99828778764580206 0.031556185440510726 -0.049251397926289027 0 0.038468552846355669 -0.98847817658445747 0.14639352737800052 -0
		 -35.679084432099756 2.1510874842858909 14.343308792762238 1;
	setAttr ".pm[76]" -type "matrix" -0.044064310719183056 -0.14803750057573375 -0.98799961282590198 0
		 0.99828778764580206 0.031556185440510726 -0.049251397926289027 0 0.038468552846355669 -0.98847817658445747 0.14639352737800052 -0
		 -21.622141265357996 1.4969094931223024 14.482042566930806 1;
	setAttr ".pm[77]" -type "matrix" -0.046726521766803482 -0.14721887520437607 -0.98799961282742177 0
		 0.99869449405102084 0.013550178981221368 -0.049251397967495905 0 0.020638306998206825 -0.98901111997445967 0.14639352735388458 -0
		 -78.56408960327667 3.0424187130609948 14.149844316139369 1;
	setAttr ".pm[78]" -type "matrix" -0.046726521766803482 -0.14721887520437607 -0.98799961282742177 0
		 0.99869449405102084 0.013550178981221368 -0.049251397967495905 0 0.020638306998206825 -0.98901111997445967 0.14639352735388458 -0
		 -64.120894238196641 3.3720275856538184 14.214941412393523 1;
	setAttr ".gm" -type "matrix" 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1;
	setAttr -s 79 ".ma";
	setAttr -s 79 ".dpf[0:78]"  4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 
		4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 
		4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4;
	setAttr -s 79 ".lw";
	setAttr -s 79 ".lw";
	setAttr ".mi" 5;
	setAttr ".ucm" yes;
	setAttr -s 79 ".ifcl";
	setAttr -s 79 ".ifcl";
createNode dagPose -n "bindPose1";
	rename -uid "617E0D7D-406A-E1EC-D9CD-61AF1DF9F9E0";
	setAttr -s 93 ".wm";
	setAttr -s 93 ".xm";
	setAttr ".xm[0]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 -0.70710678118654757 0 0 0.70710678118654757 1 1 1 no;
	setAttr ".xm[1]" -type "matrix" "xform" 1 1 1 -1.5707963267948966 -1.5073866484408736
		 1.5707963267948966 0 -3.4314998759166215e-17 -2.2808661460876465 95.896781921386719 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[2]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999989 1 -8.4954340412815775e-19
		 3.7879761270054613e-18 -0.25232786692436704 0 3.6770534515381001 7.1054273576010019e-15
		 -4.6633694517662434e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[3]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 -1.526598595380997e-19
		 3.8327957393595285e-18 0.060466399756961373 0 6.7950572967529155 1.7763568394002505e-14
		 1.8559423937125809e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1 no;
	setAttr ".xm[4]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 1.3459375357916401e-18
		 3.7858793145414413e-18 0.19104512581130384 0 7.2382278442382812 -1.9539925233402755e-14
		 1.2292061026364971e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[5]" -type "matrix" "xform" 1 0.99999999999999989 1 7.8457562572308448e-06
		 -4.1750609512244074e-14 0.10239818677280667 0 8.5238933563232422 -7.1054273576010019e-15
		 2.5229931328786502e-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[6]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 -7.8452173436827024e-06
		 9.3303177584585829e-08 0.011892487809488461 0 19.439800262451158 -1.7817309228007616e-07
		 8.1130192624775943e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[7]" -type "matrix" "xform" 1 1 1 -9.2915892070507301e-18 7.0177144030457207e-17
		 -0.41762943546079279 0 11.887765884399442 1.0658141036401503e-14 1.5994409772213136e-15 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 0.99999999999999978
		 1 no;
	setAttr ".xm[8]" -type "matrix" "xform" 1 0.99999999999999989 1 -1.7098080609365499e-06
		 3.1265086895115411e-16 0.033397375038360995 0 5.1102595329284384 -6.3948846218409017e-14
		 -4.1190754660973504e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[9]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1 1.6732006206635733e-06
		 -3.5198750386794149e-07 0.20734807648447118 0 4.9129710197448446 -4.9737991503207013e-14
		 2.0180004314720307e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[10]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 0.99999999999999944 2.8494871086844684
		 1.4107710302056788 2.6725246597991861 0 5.5162687301636311 1.3147660493850672
		 -1.4279042482376099 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[11]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999967 -0.075700955616242127
		 0.80336814696867653 -0.076070501056283102 0 17.809522628784187 1.6431300764452317e-14
		 5.6843418860808015e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 1.0000000000000007 no;
	setAttr ".xm[12]" -type "matrix" "xform" 1.0000000000000002 1 1 -2.0122792321330962e-16
		 6.2450045135165068e-17 -0.68030878144743478 0 27.771139144897504 1.3322676295501878e-14
		 -1.1368683772161603e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[13]" -type "matrix" "xform" 1.0000000000000004 1 1 0.022439294079822175
		 -0.030151140935290543 0.034659238401632195 0 9.0836915969848633 -7.1054273576010019e-14
		 9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[14]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000002 0.022439294486885784
		 -0.030151008698346637 0.034659239879545549 0 18.167383193969734 -2.8421709430404007e-14
		 7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[15]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000011 0.99999999999999956 -1.1828228767081526
		 0.025716916543067354 0.032269676501439172 0 27.251073837280284 -2.1316282072803006e-14
		 9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1 no;
	setAttr ".xm[16]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999967
		 0.99999999999999978 -0.074569197575235543 -0.0022820379734449945 -0.040463566458286797 0 3.3758335113525533
		 -0.75357073545451669 -0.18286436796188354 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999978 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[17]" -type "matrix" "xform" 1.0000000000000009 1 1.0000000000000004 1.1102230246251568e-16
		 -5.551115123125779e-17 0.5510472548888049 0 6.0982089042663432 5.6843418860808015e-14
		 1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[18]" -type "matrix" "xform" 1.0000000000000002 1 1 1.1102230246251565e-16
		 2.4980018054066027e-16 0.36249110587625905 0 5.1690001487731934 -1.4210854715202004e-14
		 4.2632564145606011e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999911
		 1 0.99999999999999956 no;
	setAttr ".xm[19]" -type "matrix" "xform" 1 0.99999999999999989 0.99999999999999967 4.4408920985006271e-16
		 9.7144514654701197e-17 0.17453292469247375 0 2.4739999771118164 4.2632564145606011e-14
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 1 no;
	setAttr ".xm[20]" -type "matrix" "xform" 1.0000000000000002 1 0.99999999999999944 -0.48466133745210704
		 -0.3408227139232512 0.20683246463072913 0 3.3143784999847554 -0.30591726303099165
		 2.3911108970642037 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[21]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 0.18311366302368809
		 0.010559986230106639 0.25889657159602564 0 4.9575676918029927 -0.14312039315700531
		 -0.19884027540683746 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 1.0000000000000007 no;
	setAttr ".xm[22]" -type "matrix" "xform" 1.0000000000000004 1 1 -5.5511151231257827e-17
		 -0 0.37152822127820773 0 3.8159999847411825 1.8474111129762605e-13 6.3948846218409017e-14 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 0.99999999999999978 no;
	setAttr ".xm[23]" -type "matrix" "xform" 1 1 1 0 -5.5511151231257827e-17 0.08581784014125636 0 2.0399999618530416
		 7.1054273576010019e-15 1.7763568394002505e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999956 1 1 no;
	setAttr ".xm[24]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999989
		 0.99999999999999967 -0.23212590879105988 -0.20611149294555786 -0.027830380771128975 0 3.3743038177490234
		 -0.54251688718794355 1.0917565822601283 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[25]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000004 0.1116285440033984
		 -0.0020409533590841928 0.51337956704180743 0 5.6455168724060023 -0.041624534875168706
		 -0.020689174532893873 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000004 no;
	setAttr ".xm[26]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 -5.5511151231257839e-17
		 1.3877787807814452e-16 0.33098423135410443 0 4.9770002365112447 -7.1054273576010019e-14
		 -9.5923269327613525e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 0.99999999999999956 no;
	setAttr ".xm[27]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 0
		 3.8857805861880474e-16 0.1600117814250466 0 2.265000104904189 3.5527136788005009e-14
		 1.5987211554602254e-13 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1 0.99999999999999978 no;
	setAttr ".xm[28]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 0.99999999999999867 1.2839421076547719
		 0.69645929885484559 0.35794391277517801 0 1.992446541786201 1.3566048145294474
		 -2.5815360546112114 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[29]" -type "matrix" "xform" 1 1.0000000000000004 1.0000000000000002 0.061621083266618436
		 -0.033724831256182378 0.40571933881715627 0 4.3779997825622416 9.9475983006414026e-14
		 -7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999956 1.0000000000000013 no;
	setAttr ".xm[30]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999989 -5.5511151231257839e-17
		 -5.5511151231257821e-17 0.17453292469247381 0 3.0859999656677246 4.2632564145606011e-14
		 7.1054273576010019e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 0.99999999999999956
		 0.99999999999999978 no;
	setAttr ".xm[31]" -type "matrix" "xform" 1 0.99999999999999956 0.99999999999999989 0.057382000604555151
		 0.12785412347368244 -0.010579529318345349 0 3.4445061683654821 -0.3846808075904562
		 -2.3793244361877459 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[32]" -type "matrix" "xform" 1.0000000000000002 1 1 2.2204460492503141e-16
		 2.2204460492503131e-16 0.40793579989913942 0 5.8770980834960902 0.043181736022219752
		 0.24087569117545549 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000004
		 1.0000000000000002 no;
	setAttr ".xm[33]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999967 0.99999999999999989 5.5511151231257876e-17
		 1.6653345369377348e-16 0.25992435299201333 0 4.0799999237060547 0 -9.0594198809412774e-14 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978 1 1 no;
	setAttr ".xm[34]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999933 1 -5.5511151231257864e-17
		 3.053113317719181e-16 0.21845240790709738 0 2.5950000286102437 7.1054273576010019e-14
		 -2.1316282072803006e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[35]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999978 0.99999999999999956 -0.20276557329418932
		 -0.27590811869800352 0.14865119937913096 0 1.1633778810501241 1.3170588016510436
		 0.51951599121093395 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999889 1.0000000000000004 no;
	setAttr ".xm[36]" -type "matrix" "xform" 1.0000000000000004 0.99999999999999978 1.0000000000000002 4.6824455033833496e-12
		 -0.037582720016429066 -0.0057004004254963374 0 9.2570457458496378 1.1546319456101628e-14
		 -9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[37]" -type "matrix" "xform" 1.0000000000000004 0.99999999999999989 1.0000000000000002 -4.8572257327350605e-17
		 7.762887554996208e-17 6.9388939039072253e-18 0 18.514091491699276 8.8817841970012523e-15
		 -9.9475983006414026e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000004 no;
	setAttr ".xm[38]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 0.99999999999999967 2.8494871086844702
		 1.4107710302056791 -0.46906799379060754 0 5.5162200927734375 1.314811229705807
		 1.4278726577758791 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1 no;
	setAttr ".xm[39]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999944 -0.075700955616242183
		 0.80336814696867653 -0.076070501056282894 0 -17.809625625610355 2.8716144648832653e-06
		 0.00043809693306684494 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999956 1.0000000000000004 no;
	setAttr ".xm[40]" -type "matrix" "xform" 1 1 1.0000000000000002 -2.0122792321330962e-16
		 2.7061686225238191e-16 -0.6803087814474349 0 -27.770694732666016 -3.4638958368304884e-14
		 5.6843418860808015e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[41]" -type "matrix" "xform" 1 1 1.0000000000000002 0.022439294079822283
		 -0.030151140935290387 0.034659238401632479 0 -9.0836620330810547 -1.4210854715202004e-14
		 -1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[42]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1.0000000000000002 0.022439294486885905
		 -0.030151008698346519 0.034659239879545889 0 -18.167304992675781 -7.1054273576010019e-15
		 -1.4210854715202004e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[43]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000007 0.99999999999999956 -1.182822876708153
		 0.025716916543067622 0.032269676501439297 0 -27.251010894775412 -7.1054273576010019e-15
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0.99999999999999978 no;
	setAttr ".xm[44]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999933
		 0.99999999999999989 -0.074569197575235072 -0.0022820379734449399 -0.040463566458286901 0 -3.3758001327514471
		 0.75400394201277265 0.18280552327632194 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[45]" -type "matrix" "xform" 1.0000000000000004 1 1.0000000000000004 1.1102230246251568e-16
		 5.5511151231257815e-17 0.55104725488880479 0 -6.0983657836914205 -0.0001238507247620646
		 1.430381864508945e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000007 1.0000000000000002 no;
	setAttr ".xm[46]" -type "matrix" "xform" 1.0000000000000007 1.0000000000000002 1.0000000000000002 5.5511151231257815e-17
		 2.4980018054066007e-16 0.36249110587625921 0 -5.1689915657043315 -7.7438591688405722e-05
		 -3.7045669152746541e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 1 0.99999999999999956 no;
	setAttr ".xm[47]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999989
		 1.0000000000000002 5.5511151231257839e-17 1.8041124150158796e-16 0.17453292469247383 0 -2.4740469455719136
		 4.577730578603223e-05 3.4385015172944122e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999933 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[48]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999978
		 0.99999999999999944 -0.48466133745210677 -0.34082271392325142 0.20683246463072907 0 -3.3146772384643484
		 0.30593535304068098 -2.3912868499755913 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[49]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000004 0.18311366302368837
		 0.010559986230106516 0.25889657159602564 0 -4.9573006629943919 0.14326146245002747
		 0.19892024993895774 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000007 no;
	setAttr ".xm[50]" -type "matrix" "xform" 1 0.99999999999999989 1.0000000000000002 1.110223024625157e-16
		 2.4980018054066027e-16 0.37152822127820773 0 -3.8160362243652344 3.0366025399075625e-05
		 3.2629206547341028e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 0.99999999999999956 no;
	setAttr ".xm[51]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000007 2.9802322609739917e-08
		 1.6653345348697833e-16 0.085817840141256277 0 -2.0399997234344625 -1.7523876529423887e-05
		 -3.1002964529847077e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 0.99999999999999978 no;
	setAttr ".xm[52]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999978
		 0.99999999999999978 -0.23212590879105943 -0.20611149294555794 -0.027830380771128815 0 -3.3742079734802175
		 0.54299175739286909 -1.0917816162109411 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[53]" -type "matrix" "xform" 1 0.99999999999999989 1.0000000000000002 0.11162854400339839
		 -0.0020409533590840857 0.51337956704180732 0 -5.6457118988037216 0.041443493217229843
		 0.02067497372626903 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000002 1.0000000000000002 no;
	setAttr ".xm[54]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000002 1.0000000000000002 1.6653345369377346e-16
		 -5.5511151231257796e-17 0.3309842313541051 0 -4.9770674705505371 -2.0846833649557084e-05
		 -2.3612021323060617e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 0.99999999999999978 no;
	setAttr ".xm[55]" -type "matrix" "xform" 1 0.99999999999999956 1 1.110223024625157e-16
		 -1.1102230246251565e-16 0.1600117814250463 0 -2.2649745941161967 5.0017570174532011e-05
		 -1.1221488421142567e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[56]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 0.99999999999999867 1.2839421076547719
		 0.69645929885484559 0.35794391277517801 0 -1.9928325414657593 -1.3566571474075317
		 2.5813255310058487 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[57]" -type "matrix" "xform" 0.99999999999999989 1 1 0.061621083266618769
		 -0.033724831256182371 0.40571933881715622 0 -4.3778247833251811 0.00042712956201285124
		 -0.00013574546028394252 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999978 1.0000000000000013 no;
	setAttr ".xm[58]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1.0000000000000002 2.2204460492503128e-16
		 2.775557561562892e-17 0.174532924692474 0 -3.0859522819519114 -1.4851160820228415e-05
		 4.5825581779013191e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1 1 no;
	setAttr ".xm[59]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999967
		 0.99999999999999989 0.057382000604555554 0.12785412347368241 -0.010579529318345288 0 -3.4445140361785747
		 0.38516682386398315 2.3793087005615163 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[60]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 1.6653345369377356e-16
		 -6.1629758220391561e-33 0.40793579989913936 0 -5.8772053718566966 -0.043412361294045354
		 -0.24095164239406408 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[61]" -type "matrix" "xform" 0.99999999999999956 0.99999999999999956
		 1 1.6653345369377363e-16 -2.7755575615628938e-17 0.25992435299201333 0 -4.079932689666748
		 5.0402059201815064e-06 3.2106661814523818e-05 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 0.99999999999999978 0.99999999999999978 1 no;
	setAttr ".xm[62]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 5.5511151231257827e-17
		 -7.7037197775489451e-34 0.21845240790709736 0 -2.5950763225555562 3.9602185992748673e-05
		 -3.5606819821509816e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1 no;
	setAttr ".xm[63]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999967 -0.20276557828828717
		 -0.2759081145953387 0.14865123738628735 0 -1.1633833646774221 -1.3170545101165771
		 -0.51951736211777799 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999978
		 0.99999999999999933 1.0000000000000004 no;
	setAttr ".xm[64]" -type "matrix" "xform" 1.0000000000000002 0.99999999999999978 1.0000000000000002 4.6825010808855376e-12
		 -0.037582720016428761 -0.0057004004254963235 0 -9.2568979263305522 1.0202637897194222e-05
		 -0.00010078256310919187 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[65]" -type "matrix" "xform" 1.0000000000000002 1 1.0000000000000002 3.4694469519536142e-17
		 1.8496489062602701e-16 -2.0816681711721682e-17 0 -18.513795852661133 2.0405275791723909e-05
		 -0.00020156512620417288 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1.0000000000000007 no;
	setAttr ".xm[66]" -type "matrix" "xform" 1 0.99999999999999989 1 0.14675668491959673
		 -0.05455096215892502 3.0794566049833967 0 -2.3657262325286723 -0.11948779225349782
		 9.9690914154052734 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[67]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999989
		 1 -1.1102230246251568e-16 -8.1532003370909958e-17 -0.087351016050521424 0 43.341262817382777
		 -2.5757174171303632e-14 1.0658141036401503e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1 1.0000000000000002 1 no;
	setAttr ".xm[68]" -type "matrix" "xform" 0.99999999999999989 1.0000000000000002 1.0000000000000002 -8.1377868058169335e-05
		 0.05377711914424417 0.04649739873768536 0 42.217948913574233 1.1102230246251565e-16
		 1.0658141036401503e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000002 1 no;
	setAttr ".xm[69]" -type "matrix" "xform" 0.99999999999999967 1 0.99999999999999978 1.2177758801357188e-15
		 -1.1379786002407858e-15 -1.5707963267948968 0 7.0094366073608354 15.237594604492184
		 -0.53894561529159546 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002
		 0.99999999999999978 0.99999999999999978 no;
	setAttr ".xm[70]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999967
		 1 -8.1261009348669198e-05 0.0045057895521491333 0.046501405584295427 0 14.072649955749519
		 6.8833827526759706e-15 0.037728950381282544 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1.0000000000000004 1.0000000000000002 1 no;
	setAttr ".xm[71]" -type "matrix" "xform" 0.99999999999999989 0.99999999999999967
		 1 -8.1261009348669198e-05 0.0045057895521491333 0.046501405584295427 0 28.145299911499034
		 8.4376949871511897e-15 0.075457900762563312 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1.0000000000000004 1.0000000000000002 1 no;
	setAttr ".xm[72]" -type "matrix" "xform" 0.99999999999999956 1 0.99999999999999989 -3.604153589139624e-12
		 0.0045065222090264426 -0.022816700021501331 0 14.447087287902804 -3.5527136788005009e-15
		 -3.5527136788005009e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[73]" -type "matrix" "xform" 0.99999999999999956 1 0.99999999999999989 -3.604153589139624e-12
		 0.0045065222090264426 -0.022816700021501331 0 28.894174575805629 -1.2434497875801753e-14
		 -3.3750779948604759e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1.0000000000000002
		 1 no;
	setAttr ".xm[74]" -type "matrix" "xform" 1 1 1 0.14675668491959665 -0.054550962158925013
		 -0.062136048606397057 0 -2.3657112121582031 -0.11004376411438344 -9.969202995300293 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[75]" -type "matrix" "xform" 0.99999999999999967 0.99999999999999967
		 0.99999999999999989 -5.5511151231257864e-17 -0 -0.087351016050520799 0 -43.341308593749993
		 6.2172489379008766e-15 5.3290705182007514e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 
		0 0 0 1 1 1 1 no;
	setAttr ".xm[76]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000011 1.0000000000000004 -8.1377868058141756e-05
		 0.053777119144244226 0.046497398737685401 0 -42.217914581298842 -3.5527136788005009e-15
		 5.3290705182007514e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[77]" -type "matrix" "xform" 0.99999999999999956 1.0000000000000002 0.99999999999999978 1.5785983631388942e-16
		 -1.110223024625157e-16 -1.5707963267948968 0 -7.0094366073608327 -15.237588882446284
		 0.53888744115829468 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0.99999999999999956
		 0.99999999999999889 0.99999999999999956 no;
	setAttr ".xm[78]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 1.0000000000000004 -8.1261009348641429e-05
		 0.0045057895521491897 0.046501405584295455 0 -14.072638511657715 1.7763568394002505e-15
		 1.9539925233402755e-14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[79]" -type "matrix" "xform" 1.0000000000000004 1.0000000000000004 1.0000000000000004 -8.1261009348641429e-05
		 0.0045057895521491897 0.046501405584295455 0 -28.145277023315437 5.0670109880135428e-06
		 -0.075448110699655402 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000004
		 1.0000000000000004 1.0000000000000002 no;
	setAttr ".xm[80]" -type "matrix" "xform" 0.99999999999999978 1 0.99999999999999978 -3.6040425792624552e-12
		 0.0045065222090265337 -0.022816700021500678 0 -14.447102546691895 8.8817841970012523e-16
		 3.5527136788005009e-15 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[81]" -type "matrix" "xform" 0.99999999999999978 1 0.99999999999999978 -3.6040425792624552e-12
		 0.0045065222090265337 -0.022816700021500678 0 -28.894205093383796 -2.2688980125806779e-06
		 -8.0748641266836785e-06 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[82]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[83]" -type "matrix" "xform" 0.99999999999999978 0.99999999999999978
		 1 1.1950811745653398 -0.68783621143055862 0.93665733272538276 0 -47.768318176269531
		 -15.69880485534668 104.4664306640625 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1
		 1 1 no;
	setAttr ".xm[84]" -type "matrix" "xform" 1.0000000000000002 1.0000000000000002 1 5.8286708792820709e-16
		 -3.8857805861880469e-16 0 0 -7.1054273576010019e-15 0 7.1054273576010019e-15 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002 1.0000000000000002
		 1 no;
	setAttr ".xm[85]" -type "matrix" "xform" 1 1 1 -1.8803756031765697 -0.59405406535441252
		 -2.347589926485619 0 43.73357009887696 -61.669849395751982 58.408111572265597 0
		 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1.0000000000000002 1.0000000000000002
		 1 no;
	setAttr ".xm[86]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[87]" -type "matrix" "xform" 1 0.99999999999999978 0.99999999999999978 1.5715746675411471
		 -1.5392348934121391 -1.4229168665858918 0 14.087671279907227 0.99425750970840454
		 8.2376375198364258 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[88]" -type "matrix" "xform" 1 0.99999999999999956 0.99999999999999978 -1.5700179860486321
		 1.5392348934121391 1.4229168665858849 0 -14.087558746337891 0.98483455181121826
		 8.2382316589355469 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[89]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[90]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[91]" -type "matrix" "xform" 1 1 1 0 0 0 0 2.8421709430404007e-14
		 0 168 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr ".xm[92]" -type "matrix" "xform" 1 1 1 0 0 0 0 0 0 -3 0 0 0 0 0 0 0
		 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 1 no;
	setAttr -s 93 ".m";
	setAttr -s 93 ".p";
	setAttr ".bp" yes;
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
	setAttr -s 2 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 6 ".s";
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
select -ne :defaultRenderGlobals;
	addAttr -ci true -h true -sn "dss" -ln "defaultSurfaceShader" -dt "string";
	setAttr ".dss" -type "string" "openPBR_shader1";
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
connectAttr "root.s" "pelvis.is";
connectAttr "pelvis.s" "spine_01.is";
connectAttr "spine_01.s" "spine_02.is";
connectAttr "spine_02.s" "spine_03.is";
connectAttr "spine_03.s" "spine_04.is";
connectAttr "spine_04.s" "spine_05.is";
connectAttr "spine_05.s" "neck_01.is";
connectAttr "neck_01.s" "neck_02.is";
connectAttr "neck_02.s" "head.is";
connectAttr "spine_05.s" "clavicle_l.is";
connectAttr "clavicle_l.s" "upperarm_l.is";
connectAttr "upperarm_l.s" "lowerarm_l.is";
connectAttr "lowerarm_l.s" "lowerarm_twist_02_l.is";
connectAttr "lowerarm_l.s" "lowerarm_twist_01_l.is";
connectAttr "lowerarm_l.s" "hand_l.is";
connectAttr "hand_l.s" "middle_metacarpal_l.is";
connectAttr "middle_metacarpal_l.s" "middle_01_l.is";
connectAttr "middle_01_l.s" "middle_02_l.is";
connectAttr "middle_02_l.s" "middle_03_l.is";
connectAttr "hand_l.s" "pinky_metacarpal_l.is";
connectAttr "pinky_metacarpal_l.s" "pinky_01_l.is";
connectAttr "pinky_01_l.s" "pinky_02_l.is";
connectAttr "pinky_02_l.s" "pinky_03_l.is";
connectAttr "hand_l.s" "ring_metacarpal_l.is";
connectAttr "ring_metacarpal_l.s" "ring_01_l.is";
connectAttr "ring_01_l.s" "ring_02_l.is";
connectAttr "ring_02_l.s" "ring_03_l.is";
connectAttr "hand_l.s" "thumb_01_l.is";
connectAttr "thumb_01_l.s" "thumb_02_l.is";
connectAttr "thumb_02_l.s" "thumb_03_l.is";
connectAttr "hand_l.s" "index_metacarpal_l.is";
connectAttr "index_metacarpal_l.s" "index_01_l.is";
connectAttr "index_01_l.s" "index_02_l.is";
connectAttr "index_02_l.s" "index_03_l.is";
connectAttr "hand_l.s" "weapon_l.is";
connectAttr "upperarm_l.s" "upperarm_twist_01_l.is";
connectAttr "upperarm_l.s" "upperarm_twist_02_l.is";
connectAttr "spine_05.s" "clavicle_r.is";
connectAttr "clavicle_r.s" "upperarm_r.is";
connectAttr "upperarm_r.s" "lowerarm_r.is";
connectAttr "lowerarm_r.s" "lowerarm_twist_02_r.is";
connectAttr "lowerarm_r.s" "lowerarm_twist_01_r.is";
connectAttr "lowerarm_r.s" "hand_r.is";
connectAttr "hand_r.s" "middle_metacarpal_r.is";
connectAttr "middle_metacarpal_r.s" "middle_01_r.is";
connectAttr "middle_01_r.s" "middle_02_r.is";
connectAttr "middle_02_r.s" "middle_03_r.is";
connectAttr "hand_r.s" "pinky_metacarpal_r.is";
connectAttr "pinky_metacarpal_r.s" "pinky_01_r.is";
connectAttr "pinky_01_r.s" "pinky_02_r.is";
connectAttr "pinky_02_r.s" "pinky_03_r.is";
connectAttr "hand_r.s" "ring_metacarpal_r.is";
connectAttr "ring_metacarpal_r.s" "ring_01_r.is";
connectAttr "ring_01_r.s" "ring_02_r.is";
connectAttr "ring_02_r.s" "ring_03_r.is";
connectAttr "hand_r.s" "thumb_01_r.is";
connectAttr "thumb_01_r.s" "thumb_02_r.is";
connectAttr "thumb_02_r.s" "thumb_03_r.is";
connectAttr "hand_r.s" "index_metacarpal_r.is";
connectAttr "index_metacarpal_r.s" "index_01_r.is";
connectAttr "index_01_r.s" "index_02_r.is";
connectAttr "index_02_r.s" "index_03_r.is";
connectAttr "hand_r.s" "weapon_r.is";
connectAttr "upperarm_r.s" "upperarm_twist_01_r.is";
connectAttr "upperarm_r.s" "upperarm_twist_02_r.is";
connectAttr "pelvis.s" "thigh_r.is";
connectAttr "thigh_r.s" "calf_r.is";
connectAttr "calf_r.s" "foot_r.is";
connectAttr "foot_r.s" "ball_r.is";
connectAttr "calf_r.s" "calf_twist_02_r.is";
connectAttr "calf_r.s" "calf_twist_01_r.is";
connectAttr "thigh_r.s" "thigh_twist_01_r.is";
connectAttr "thigh_r.s" "thigh_twist_02_r.is";
connectAttr "pelvis.s" "thigh_l.is";
connectAttr "thigh_l.s" "calf_l.is";
connectAttr "calf_l.s" "foot_l.is";
connectAttr "foot_l.s" "ball_l.is";
connectAttr "calf_l.s" "calf_twist_02_l.is";
connectAttr "calf_l.s" "calf_twist_01_l.is";
connectAttr "thigh_l.s" "thigh_twist_01_l.is";
connectAttr "thigh_l.s" "thigh_twist_02_l.is";
connectAttr "root.s" "ik_hand_root.is";
connectAttr "ik_hand_root.s" "ik_hand_gun.is";
connectAttr "ik_hand_gun.s" "ik_hand_r.is";
connectAttr "ik_hand_gun.s" "ik_hand_l.is";
connectAttr "root.s" "ik_foot_root.is";
connectAttr "ik_foot_root.s" "ik_foot_l.is";
connectAttr "ik_foot_root.s" "ik_foot_r.is";
connectAttr "root.s" "interaction.is";
connectAttr "root.s" "center_of_mass.is";
connectAttr "root.s" "camera_root.is";
connectAttr "camera_root.s" "camera_bone.is";
connectAttr "Cape_skinCluster.og[0]" "CapeShape.i";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "CapeShapeOrig.w" "Cape_skinCluster.ip[0].ig";
connectAttr "CapeShapeOrig.o" "Cape_skinCluster.orggeom[0]";
connectAttr "pelvis.wm" "Cape_skinCluster.ma[0]";
connectAttr "spine_01.wm" "Cape_skinCluster.ma[1]";
connectAttr "spine_02.wm" "Cape_skinCluster.ma[2]";
connectAttr "spine_03.wm" "Cape_skinCluster.ma[3]";
connectAttr "spine_04.wm" "Cape_skinCluster.ma[4]";
connectAttr "spine_05.wm" "Cape_skinCluster.ma[5]";
connectAttr "neck_01.wm" "Cape_skinCluster.ma[6]";
connectAttr "neck_02.wm" "Cape_skinCluster.ma[7]";
connectAttr "head.wm" "Cape_skinCluster.ma[8]";
connectAttr "clavicle_l.wm" "Cape_skinCluster.ma[9]";
connectAttr "upperarm_l.wm" "Cape_skinCluster.ma[10]";
connectAttr "lowerarm_l.wm" "Cape_skinCluster.ma[11]";
connectAttr "lowerarm_twist_02_l.wm" "Cape_skinCluster.ma[12]";
connectAttr "lowerarm_twist_01_l.wm" "Cape_skinCluster.ma[13]";
connectAttr "hand_l.wm" "Cape_skinCluster.ma[14]";
connectAttr "middle_metacarpal_l.wm" "Cape_skinCluster.ma[15]";
connectAttr "middle_01_l.wm" "Cape_skinCluster.ma[16]";
connectAttr "middle_02_l.wm" "Cape_skinCluster.ma[17]";
connectAttr "middle_03_l.wm" "Cape_skinCluster.ma[18]";
connectAttr "pinky_metacarpal_l.wm" "Cape_skinCluster.ma[19]";
connectAttr "pinky_01_l.wm" "Cape_skinCluster.ma[20]";
connectAttr "pinky_02_l.wm" "Cape_skinCluster.ma[21]";
connectAttr "pinky_03_l.wm" "Cape_skinCluster.ma[22]";
connectAttr "ring_metacarpal_l.wm" "Cape_skinCluster.ma[23]";
connectAttr "ring_01_l.wm" "Cape_skinCluster.ma[24]";
connectAttr "ring_02_l.wm" "Cape_skinCluster.ma[25]";
connectAttr "ring_03_l.wm" "Cape_skinCluster.ma[26]";
connectAttr "thumb_01_l.wm" "Cape_skinCluster.ma[27]";
connectAttr "thumb_02_l.wm" "Cape_skinCluster.ma[28]";
connectAttr "thumb_03_l.wm" "Cape_skinCluster.ma[29]";
connectAttr "index_metacarpal_l.wm" "Cape_skinCluster.ma[30]";
connectAttr "index_01_l.wm" "Cape_skinCluster.ma[31]";
connectAttr "index_02_l.wm" "Cape_skinCluster.ma[32]";
connectAttr "index_03_l.wm" "Cape_skinCluster.ma[33]";
connectAttr "upperarm_twist_01_l.wm" "Cape_skinCluster.ma[34]";
connectAttr "upperarm_twist_02_l.wm" "Cape_skinCluster.ma[35]";
connectAttr "clavicle_r.wm" "Cape_skinCluster.ma[36]";
connectAttr "upperarm_r.wm" "Cape_skinCluster.ma[37]";
connectAttr "lowerarm_r.wm" "Cape_skinCluster.ma[38]";
connectAttr "lowerarm_twist_02_r.wm" "Cape_skinCluster.ma[39]";
connectAttr "lowerarm_twist_01_r.wm" "Cape_skinCluster.ma[40]";
connectAttr "hand_r.wm" "Cape_skinCluster.ma[41]";
connectAttr "middle_metacarpal_r.wm" "Cape_skinCluster.ma[42]";
connectAttr "middle_01_r.wm" "Cape_skinCluster.ma[43]";
connectAttr "middle_02_r.wm" "Cape_skinCluster.ma[44]";
connectAttr "middle_03_r.wm" "Cape_skinCluster.ma[45]";
connectAttr "pinky_metacarpal_r.wm" "Cape_skinCluster.ma[46]";
connectAttr "pinky_01_r.wm" "Cape_skinCluster.ma[47]";
connectAttr "pinky_02_r.wm" "Cape_skinCluster.ma[48]";
connectAttr "pinky_03_r.wm" "Cape_skinCluster.ma[49]";
connectAttr "ring_metacarpal_r.wm" "Cape_skinCluster.ma[50]";
connectAttr "ring_01_r.wm" "Cape_skinCluster.ma[51]";
connectAttr "ring_02_r.wm" "Cape_skinCluster.ma[52]";
connectAttr "ring_03_r.wm" "Cape_skinCluster.ma[53]";
connectAttr "thumb_01_r.wm" "Cape_skinCluster.ma[54]";
connectAttr "thumb_02_r.wm" "Cape_skinCluster.ma[55]";
connectAttr "thumb_03_r.wm" "Cape_skinCluster.ma[56]";
connectAttr "index_metacarpal_r.wm" "Cape_skinCluster.ma[57]";
connectAttr "index_01_r.wm" "Cape_skinCluster.ma[58]";
connectAttr "index_02_r.wm" "Cape_skinCluster.ma[59]";
connectAttr "index_03_r.wm" "Cape_skinCluster.ma[60]";
connectAttr "upperarm_twist_01_r.wm" "Cape_skinCluster.ma[61]";
connectAttr "upperarm_twist_02_r.wm" "Cape_skinCluster.ma[62]";
connectAttr "thigh_r.wm" "Cape_skinCluster.ma[63]";
connectAttr "calf_r.wm" "Cape_skinCluster.ma[64]";
connectAttr "foot_r.wm" "Cape_skinCluster.ma[65]";
connectAttr "ball_r.wm" "Cape_skinCluster.ma[66]";
connectAttr "calf_twist_02_r.wm" "Cape_skinCluster.ma[67]";
connectAttr "calf_twist_01_r.wm" "Cape_skinCluster.ma[68]";
connectAttr "thigh_twist_01_r.wm" "Cape_skinCluster.ma[69]";
connectAttr "thigh_twist_02_r.wm" "Cape_skinCluster.ma[70]";
connectAttr "thigh_l.wm" "Cape_skinCluster.ma[71]";
connectAttr "calf_l.wm" "Cape_skinCluster.ma[72]";
connectAttr "foot_l.wm" "Cape_skinCluster.ma[73]";
connectAttr "ball_l.wm" "Cape_skinCluster.ma[74]";
connectAttr "calf_twist_02_l.wm" "Cape_skinCluster.ma[75]";
connectAttr "calf_twist_01_l.wm" "Cape_skinCluster.ma[76]";
connectAttr "thigh_twist_01_l.wm" "Cape_skinCluster.ma[77]";
connectAttr "thigh_twist_02_l.wm" "Cape_skinCluster.ma[78]";
connectAttr "pelvis.liw" "Cape_skinCluster.lw[0]";
connectAttr "spine_01.liw" "Cape_skinCluster.lw[1]";
connectAttr "spine_02.liw" "Cape_skinCluster.lw[2]";
connectAttr "spine_03.liw" "Cape_skinCluster.lw[3]";
connectAttr "spine_04.liw" "Cape_skinCluster.lw[4]";
connectAttr "spine_05.liw" "Cape_skinCluster.lw[5]";
connectAttr "neck_01.liw" "Cape_skinCluster.lw[6]";
connectAttr "neck_02.liw" "Cape_skinCluster.lw[7]";
connectAttr "head.liw" "Cape_skinCluster.lw[8]";
connectAttr "clavicle_l.liw" "Cape_skinCluster.lw[9]";
connectAttr "upperarm_l.liw" "Cape_skinCluster.lw[10]";
connectAttr "lowerarm_l.liw" "Cape_skinCluster.lw[11]";
connectAttr "lowerarm_twist_02_l.liw" "Cape_skinCluster.lw[12]";
connectAttr "lowerarm_twist_01_l.liw" "Cape_skinCluster.lw[13]";
connectAttr "hand_l.liw" "Cape_skinCluster.lw[14]";
connectAttr "middle_metacarpal_l.liw" "Cape_skinCluster.lw[15]";
connectAttr "middle_01_l.liw" "Cape_skinCluster.lw[16]";
connectAttr "middle_02_l.liw" "Cape_skinCluster.lw[17]";
connectAttr "middle_03_l.liw" "Cape_skinCluster.lw[18]";
connectAttr "pinky_metacarpal_l.liw" "Cape_skinCluster.lw[19]";
connectAttr "pinky_01_l.liw" "Cape_skinCluster.lw[20]";
connectAttr "pinky_02_l.liw" "Cape_skinCluster.lw[21]";
connectAttr "pinky_03_l.liw" "Cape_skinCluster.lw[22]";
connectAttr "ring_metacarpal_l.liw" "Cape_skinCluster.lw[23]";
connectAttr "ring_01_l.liw" "Cape_skinCluster.lw[24]";
connectAttr "ring_02_l.liw" "Cape_skinCluster.lw[25]";
connectAttr "ring_03_l.liw" "Cape_skinCluster.lw[26]";
connectAttr "thumb_01_l.liw" "Cape_skinCluster.lw[27]";
connectAttr "thumb_02_l.liw" "Cape_skinCluster.lw[28]";
connectAttr "thumb_03_l.liw" "Cape_skinCluster.lw[29]";
connectAttr "index_metacarpal_l.liw" "Cape_skinCluster.lw[30]";
connectAttr "index_01_l.liw" "Cape_skinCluster.lw[31]";
connectAttr "index_02_l.liw" "Cape_skinCluster.lw[32]";
connectAttr "index_03_l.liw" "Cape_skinCluster.lw[33]";
connectAttr "upperarm_twist_01_l.liw" "Cape_skinCluster.lw[34]";
connectAttr "upperarm_twist_02_l.liw" "Cape_skinCluster.lw[35]";
connectAttr "clavicle_r.liw" "Cape_skinCluster.lw[36]";
connectAttr "upperarm_r.liw" "Cape_skinCluster.lw[37]";
connectAttr "lowerarm_r.liw" "Cape_skinCluster.lw[38]";
connectAttr "lowerarm_twist_02_r.liw" "Cape_skinCluster.lw[39]";
connectAttr "lowerarm_twist_01_r.liw" "Cape_skinCluster.lw[40]";
connectAttr "hand_r.liw" "Cape_skinCluster.lw[41]";
connectAttr "middle_metacarpal_r.liw" "Cape_skinCluster.lw[42]";
connectAttr "middle_01_r.liw" "Cape_skinCluster.lw[43]";
connectAttr "middle_02_r.liw" "Cape_skinCluster.lw[44]";
connectAttr "middle_03_r.liw" "Cape_skinCluster.lw[45]";
connectAttr "pinky_metacarpal_r.liw" "Cape_skinCluster.lw[46]";
connectAttr "pinky_01_r.liw" "Cape_skinCluster.lw[47]";
connectAttr "pinky_02_r.liw" "Cape_skinCluster.lw[48]";
connectAttr "pinky_03_r.liw" "Cape_skinCluster.lw[49]";
connectAttr "ring_metacarpal_r.liw" "Cape_skinCluster.lw[50]";
connectAttr "ring_01_r.liw" "Cape_skinCluster.lw[51]";
connectAttr "ring_02_r.liw" "Cape_skinCluster.lw[52]";
connectAttr "ring_03_r.liw" "Cape_skinCluster.lw[53]";
connectAttr "thumb_01_r.liw" "Cape_skinCluster.lw[54]";
connectAttr "thumb_02_r.liw" "Cape_skinCluster.lw[55]";
connectAttr "thumb_03_r.liw" "Cape_skinCluster.lw[56]";
connectAttr "index_metacarpal_r.liw" "Cape_skinCluster.lw[57]";
connectAttr "index_01_r.liw" "Cape_skinCluster.lw[58]";
connectAttr "index_02_r.liw" "Cape_skinCluster.lw[59]";
connectAttr "index_03_r.liw" "Cape_skinCluster.lw[60]";
connectAttr "upperarm_twist_01_r.liw" "Cape_skinCluster.lw[61]";
connectAttr "upperarm_twist_02_r.liw" "Cape_skinCluster.lw[62]";
connectAttr "thigh_r.liw" "Cape_skinCluster.lw[63]";
connectAttr "calf_r.liw" "Cape_skinCluster.lw[64]";
connectAttr "foot_r.liw" "Cape_skinCluster.lw[65]";
connectAttr "ball_r.liw" "Cape_skinCluster.lw[66]";
connectAttr "calf_twist_02_r.liw" "Cape_skinCluster.lw[67]";
connectAttr "calf_twist_01_r.liw" "Cape_skinCluster.lw[68]";
connectAttr "thigh_twist_01_r.liw" "Cape_skinCluster.lw[69]";
connectAttr "thigh_twist_02_r.liw" "Cape_skinCluster.lw[70]";
connectAttr "thigh_l.liw" "Cape_skinCluster.lw[71]";
connectAttr "calf_l.liw" "Cape_skinCluster.lw[72]";
connectAttr "foot_l.liw" "Cape_skinCluster.lw[73]";
connectAttr "ball_l.liw" "Cape_skinCluster.lw[74]";
connectAttr "calf_twist_02_l.liw" "Cape_skinCluster.lw[75]";
connectAttr "calf_twist_01_l.liw" "Cape_skinCluster.lw[76]";
connectAttr "thigh_twist_01_l.liw" "Cape_skinCluster.lw[77]";
connectAttr "thigh_twist_02_l.liw" "Cape_skinCluster.lw[78]";
connectAttr "pelvis.obcc" "Cape_skinCluster.ifcl[0]";
connectAttr "spine_01.obcc" "Cape_skinCluster.ifcl[1]";
connectAttr "spine_02.obcc" "Cape_skinCluster.ifcl[2]";
connectAttr "spine_03.obcc" "Cape_skinCluster.ifcl[3]";
connectAttr "spine_04.obcc" "Cape_skinCluster.ifcl[4]";
connectAttr "spine_05.obcc" "Cape_skinCluster.ifcl[5]";
connectAttr "neck_01.obcc" "Cape_skinCluster.ifcl[6]";
connectAttr "neck_02.obcc" "Cape_skinCluster.ifcl[7]";
connectAttr "head.obcc" "Cape_skinCluster.ifcl[8]";
connectAttr "clavicle_l.obcc" "Cape_skinCluster.ifcl[9]";
connectAttr "upperarm_l.obcc" "Cape_skinCluster.ifcl[10]";
connectAttr "lowerarm_l.obcc" "Cape_skinCluster.ifcl[11]";
connectAttr "lowerarm_twist_02_l.obcc" "Cape_skinCluster.ifcl[12]";
connectAttr "lowerarm_twist_01_l.obcc" "Cape_skinCluster.ifcl[13]";
connectAttr "hand_l.obcc" "Cape_skinCluster.ifcl[14]";
connectAttr "middle_metacarpal_l.obcc" "Cape_skinCluster.ifcl[15]";
connectAttr "middle_01_l.obcc" "Cape_skinCluster.ifcl[16]";
connectAttr "middle_02_l.obcc" "Cape_skinCluster.ifcl[17]";
connectAttr "middle_03_l.obcc" "Cape_skinCluster.ifcl[18]";
connectAttr "pinky_metacarpal_l.obcc" "Cape_skinCluster.ifcl[19]";
connectAttr "pinky_01_l.obcc" "Cape_skinCluster.ifcl[20]";
connectAttr "pinky_02_l.obcc" "Cape_skinCluster.ifcl[21]";
connectAttr "pinky_03_l.obcc" "Cape_skinCluster.ifcl[22]";
connectAttr "ring_metacarpal_l.obcc" "Cape_skinCluster.ifcl[23]";
connectAttr "ring_01_l.obcc" "Cape_skinCluster.ifcl[24]";
connectAttr "ring_02_l.obcc" "Cape_skinCluster.ifcl[25]";
connectAttr "ring_03_l.obcc" "Cape_skinCluster.ifcl[26]";
connectAttr "thumb_01_l.obcc" "Cape_skinCluster.ifcl[27]";
connectAttr "thumb_02_l.obcc" "Cape_skinCluster.ifcl[28]";
connectAttr "thumb_03_l.obcc" "Cape_skinCluster.ifcl[29]";
connectAttr "index_metacarpal_l.obcc" "Cape_skinCluster.ifcl[30]";
connectAttr "index_01_l.obcc" "Cape_skinCluster.ifcl[31]";
connectAttr "index_02_l.obcc" "Cape_skinCluster.ifcl[32]";
connectAttr "index_03_l.obcc" "Cape_skinCluster.ifcl[33]";
connectAttr "upperarm_twist_01_l.obcc" "Cape_skinCluster.ifcl[34]";
connectAttr "upperarm_twist_02_l.obcc" "Cape_skinCluster.ifcl[35]";
connectAttr "clavicle_r.obcc" "Cape_skinCluster.ifcl[36]";
connectAttr "upperarm_r.obcc" "Cape_skinCluster.ifcl[37]";
connectAttr "lowerarm_r.obcc" "Cape_skinCluster.ifcl[38]";
connectAttr "lowerarm_twist_02_r.obcc" "Cape_skinCluster.ifcl[39]";
connectAttr "lowerarm_twist_01_r.obcc" "Cape_skinCluster.ifcl[40]";
connectAttr "hand_r.obcc" "Cape_skinCluster.ifcl[41]";
connectAttr "middle_metacarpal_r.obcc" "Cape_skinCluster.ifcl[42]";
connectAttr "middle_01_r.obcc" "Cape_skinCluster.ifcl[43]";
connectAttr "middle_02_r.obcc" "Cape_skinCluster.ifcl[44]";
connectAttr "middle_03_r.obcc" "Cape_skinCluster.ifcl[45]";
connectAttr "pinky_metacarpal_r.obcc" "Cape_skinCluster.ifcl[46]";
connectAttr "pinky_01_r.obcc" "Cape_skinCluster.ifcl[47]";
connectAttr "pinky_02_r.obcc" "Cape_skinCluster.ifcl[48]";
connectAttr "pinky_03_r.obcc" "Cape_skinCluster.ifcl[49]";
connectAttr "ring_metacarpal_r.obcc" "Cape_skinCluster.ifcl[50]";
connectAttr "ring_01_r.obcc" "Cape_skinCluster.ifcl[51]";
connectAttr "ring_02_r.obcc" "Cape_skinCluster.ifcl[52]";
connectAttr "ring_03_r.obcc" "Cape_skinCluster.ifcl[53]";
connectAttr "thumb_01_r.obcc" "Cape_skinCluster.ifcl[54]";
connectAttr "thumb_02_r.obcc" "Cape_skinCluster.ifcl[55]";
connectAttr "thumb_03_r.obcc" "Cape_skinCluster.ifcl[56]";
connectAttr "index_metacarpal_r.obcc" "Cape_skinCluster.ifcl[57]";
connectAttr "index_01_r.obcc" "Cape_skinCluster.ifcl[58]";
connectAttr "index_02_r.obcc" "Cape_skinCluster.ifcl[59]";
connectAttr "index_03_r.obcc" "Cape_skinCluster.ifcl[60]";
connectAttr "upperarm_twist_01_r.obcc" "Cape_skinCluster.ifcl[61]";
connectAttr "upperarm_twist_02_r.obcc" "Cape_skinCluster.ifcl[62]";
connectAttr "thigh_r.obcc" "Cape_skinCluster.ifcl[63]";
connectAttr "calf_r.obcc" "Cape_skinCluster.ifcl[64]";
connectAttr "foot_r.obcc" "Cape_skinCluster.ifcl[65]";
connectAttr "ball_r.obcc" "Cape_skinCluster.ifcl[66]";
connectAttr "calf_twist_02_r.obcc" "Cape_skinCluster.ifcl[67]";
connectAttr "calf_twist_01_r.obcc" "Cape_skinCluster.ifcl[68]";
connectAttr "thigh_twist_01_r.obcc" "Cape_skinCluster.ifcl[69]";
connectAttr "thigh_twist_02_r.obcc" "Cape_skinCluster.ifcl[70]";
connectAttr "thigh_l.obcc" "Cape_skinCluster.ifcl[71]";
connectAttr "calf_l.obcc" "Cape_skinCluster.ifcl[72]";
connectAttr "foot_l.obcc" "Cape_skinCluster.ifcl[73]";
connectAttr "ball_l.obcc" "Cape_skinCluster.ifcl[74]";
connectAttr "calf_twist_02_l.obcc" "Cape_skinCluster.ifcl[75]";
connectAttr "calf_twist_01_l.obcc" "Cape_skinCluster.ifcl[76]";
connectAttr "thigh_twist_01_l.obcc" "Cape_skinCluster.ifcl[77]";
connectAttr "thigh_twist_02_l.obcc" "Cape_skinCluster.ifcl[78]";
connectAttr "bindPose1.msg" "Cape_skinCluster.bp";
connectAttr "root.msg" "bindPose1.m[0]";
connectAttr "pelvis.msg" "bindPose1.m[1]";
connectAttr "spine_01.msg" "bindPose1.m[2]";
connectAttr "spine_02.msg" "bindPose1.m[3]";
connectAttr "spine_03.msg" "bindPose1.m[4]";
connectAttr "spine_04.msg" "bindPose1.m[5]";
connectAttr "spine_05.msg" "bindPose1.m[6]";
connectAttr "neck_01.msg" "bindPose1.m[7]";
connectAttr "neck_02.msg" "bindPose1.m[8]";
connectAttr "head.msg" "bindPose1.m[9]";
connectAttr "clavicle_l.msg" "bindPose1.m[10]";
connectAttr "upperarm_l.msg" "bindPose1.m[11]";
connectAttr "lowerarm_l.msg" "bindPose1.m[12]";
connectAttr "lowerarm_twist_02_l.msg" "bindPose1.m[13]";
connectAttr "lowerarm_twist_01_l.msg" "bindPose1.m[14]";
connectAttr "hand_l.msg" "bindPose1.m[15]";
connectAttr "middle_metacarpal_l.msg" "bindPose1.m[16]";
connectAttr "middle_01_l.msg" "bindPose1.m[17]";
connectAttr "middle_02_l.msg" "bindPose1.m[18]";
connectAttr "middle_03_l.msg" "bindPose1.m[19]";
connectAttr "pinky_metacarpal_l.msg" "bindPose1.m[20]";
connectAttr "pinky_01_l.msg" "bindPose1.m[21]";
connectAttr "pinky_02_l.msg" "bindPose1.m[22]";
connectAttr "pinky_03_l.msg" "bindPose1.m[23]";
connectAttr "ring_metacarpal_l.msg" "bindPose1.m[24]";
connectAttr "ring_01_l.msg" "bindPose1.m[25]";
connectAttr "ring_02_l.msg" "bindPose1.m[26]";
connectAttr "ring_03_l.msg" "bindPose1.m[27]";
connectAttr "thumb_01_l.msg" "bindPose1.m[28]";
connectAttr "thumb_02_l.msg" "bindPose1.m[29]";
connectAttr "thumb_03_l.msg" "bindPose1.m[30]";
connectAttr "index_metacarpal_l.msg" "bindPose1.m[31]";
connectAttr "index_01_l.msg" "bindPose1.m[32]";
connectAttr "index_02_l.msg" "bindPose1.m[33]";
connectAttr "index_03_l.msg" "bindPose1.m[34]";
connectAttr "weapon_l.msg" "bindPose1.m[35]";
connectAttr "upperarm_twist_01_l.msg" "bindPose1.m[36]";
connectAttr "upperarm_twist_02_l.msg" "bindPose1.m[37]";
connectAttr "clavicle_r.msg" "bindPose1.m[38]";
connectAttr "upperarm_r.msg" "bindPose1.m[39]";
connectAttr "lowerarm_r.msg" "bindPose1.m[40]";
connectAttr "lowerarm_twist_02_r.msg" "bindPose1.m[41]";
connectAttr "lowerarm_twist_01_r.msg" "bindPose1.m[42]";
connectAttr "hand_r.msg" "bindPose1.m[43]";
connectAttr "middle_metacarpal_r.msg" "bindPose1.m[44]";
connectAttr "middle_01_r.msg" "bindPose1.m[45]";
connectAttr "middle_02_r.msg" "bindPose1.m[46]";
connectAttr "middle_03_r.msg" "bindPose1.m[47]";
connectAttr "pinky_metacarpal_r.msg" "bindPose1.m[48]";
connectAttr "pinky_01_r.msg" "bindPose1.m[49]";
connectAttr "pinky_02_r.msg" "bindPose1.m[50]";
connectAttr "pinky_03_r.msg" "bindPose1.m[51]";
connectAttr "ring_metacarpal_r.msg" "bindPose1.m[52]";
connectAttr "ring_01_r.msg" "bindPose1.m[53]";
connectAttr "ring_02_r.msg" "bindPose1.m[54]";
connectAttr "ring_03_r.msg" "bindPose1.m[55]";
connectAttr "thumb_01_r.msg" "bindPose1.m[56]";
connectAttr "thumb_02_r.msg" "bindPose1.m[57]";
connectAttr "thumb_03_r.msg" "bindPose1.m[58]";
connectAttr "index_metacarpal_r.msg" "bindPose1.m[59]";
connectAttr "index_01_r.msg" "bindPose1.m[60]";
connectAttr "index_02_r.msg" "bindPose1.m[61]";
connectAttr "index_03_r.msg" "bindPose1.m[62]";
connectAttr "weapon_r.msg" "bindPose1.m[63]";
connectAttr "upperarm_twist_01_r.msg" "bindPose1.m[64]";
connectAttr "upperarm_twist_02_r.msg" "bindPose1.m[65]";
connectAttr "thigh_r.msg" "bindPose1.m[66]";
connectAttr "calf_r.msg" "bindPose1.m[67]";
connectAttr "foot_r.msg" "bindPose1.m[68]";
connectAttr "ball_r.msg" "bindPose1.m[69]";
connectAttr "calf_twist_02_r.msg" "bindPose1.m[70]";
connectAttr "calf_twist_01_r.msg" "bindPose1.m[71]";
connectAttr "thigh_twist_01_r.msg" "bindPose1.m[72]";
connectAttr "thigh_twist_02_r.msg" "bindPose1.m[73]";
connectAttr "thigh_l.msg" "bindPose1.m[74]";
connectAttr "calf_l.msg" "bindPose1.m[75]";
connectAttr "foot_l.msg" "bindPose1.m[76]";
connectAttr "ball_l.msg" "bindPose1.m[77]";
connectAttr "calf_twist_02_l.msg" "bindPose1.m[78]";
connectAttr "calf_twist_01_l.msg" "bindPose1.m[79]";
connectAttr "thigh_twist_01_l.msg" "bindPose1.m[80]";
connectAttr "thigh_twist_02_l.msg" "bindPose1.m[81]";
connectAttr "ik_hand_root.msg" "bindPose1.m[82]";
connectAttr "ik_hand_gun.msg" "bindPose1.m[83]";
connectAttr "ik_hand_r.msg" "bindPose1.m[84]";
connectAttr "ik_hand_l.msg" "bindPose1.m[85]";
connectAttr "ik_foot_root.msg" "bindPose1.m[86]";
connectAttr "ik_foot_l.msg" "bindPose1.m[87]";
connectAttr "ik_foot_r.msg" "bindPose1.m[88]";
connectAttr "interaction.msg" "bindPose1.m[89]";
connectAttr "center_of_mass.msg" "bindPose1.m[90]";
connectAttr "camera_root.msg" "bindPose1.m[91]";
connectAttr "camera_bone.msg" "bindPose1.m[92]";
connectAttr "bindPose1.w" "bindPose1.p[0]";
connectAttr "bindPose1.m[0]" "bindPose1.p[1]";
connectAttr "bindPose1.m[1]" "bindPose1.p[2]";
connectAttr "bindPose1.m[2]" "bindPose1.p[3]";
connectAttr "bindPose1.m[3]" "bindPose1.p[4]";
connectAttr "bindPose1.m[4]" "bindPose1.p[5]";
connectAttr "bindPose1.m[5]" "bindPose1.p[6]";
connectAttr "bindPose1.m[6]" "bindPose1.p[7]";
connectAttr "bindPose1.m[7]" "bindPose1.p[8]";
connectAttr "bindPose1.m[8]" "bindPose1.p[9]";
connectAttr "bindPose1.m[6]" "bindPose1.p[10]";
connectAttr "bindPose1.m[10]" "bindPose1.p[11]";
connectAttr "bindPose1.m[11]" "bindPose1.p[12]";
connectAttr "bindPose1.m[12]" "bindPose1.p[13]";
connectAttr "bindPose1.m[12]" "bindPose1.p[14]";
connectAttr "bindPose1.m[12]" "bindPose1.p[15]";
connectAttr "bindPose1.m[15]" "bindPose1.p[16]";
connectAttr "bindPose1.m[16]" "bindPose1.p[17]";
connectAttr "bindPose1.m[17]" "bindPose1.p[18]";
connectAttr "bindPose1.m[18]" "bindPose1.p[19]";
connectAttr "bindPose1.m[15]" "bindPose1.p[20]";
connectAttr "bindPose1.m[20]" "bindPose1.p[21]";
connectAttr "bindPose1.m[21]" "bindPose1.p[22]";
connectAttr "bindPose1.m[22]" "bindPose1.p[23]";
connectAttr "bindPose1.m[15]" "bindPose1.p[24]";
connectAttr "bindPose1.m[24]" "bindPose1.p[25]";
connectAttr "bindPose1.m[25]" "bindPose1.p[26]";
connectAttr "bindPose1.m[26]" "bindPose1.p[27]";
connectAttr "bindPose1.m[15]" "bindPose1.p[28]";
connectAttr "bindPose1.m[28]" "bindPose1.p[29]";
connectAttr "bindPose1.m[29]" "bindPose1.p[30]";
connectAttr "bindPose1.m[15]" "bindPose1.p[31]";
connectAttr "bindPose1.m[31]" "bindPose1.p[32]";
connectAttr "bindPose1.m[32]" "bindPose1.p[33]";
connectAttr "bindPose1.m[33]" "bindPose1.p[34]";
connectAttr "bindPose1.m[15]" "bindPose1.p[35]";
connectAttr "bindPose1.m[11]" "bindPose1.p[36]";
connectAttr "bindPose1.m[11]" "bindPose1.p[37]";
connectAttr "bindPose1.m[6]" "bindPose1.p[38]";
connectAttr "bindPose1.m[38]" "bindPose1.p[39]";
connectAttr "bindPose1.m[39]" "bindPose1.p[40]";
connectAttr "bindPose1.m[40]" "bindPose1.p[41]";
connectAttr "bindPose1.m[40]" "bindPose1.p[42]";
connectAttr "bindPose1.m[40]" "bindPose1.p[43]";
connectAttr "bindPose1.m[43]" "bindPose1.p[44]";
connectAttr "bindPose1.m[44]" "bindPose1.p[45]";
connectAttr "bindPose1.m[45]" "bindPose1.p[46]";
connectAttr "bindPose1.m[46]" "bindPose1.p[47]";
connectAttr "bindPose1.m[43]" "bindPose1.p[48]";
connectAttr "bindPose1.m[48]" "bindPose1.p[49]";
connectAttr "bindPose1.m[49]" "bindPose1.p[50]";
connectAttr "bindPose1.m[50]" "bindPose1.p[51]";
connectAttr "bindPose1.m[43]" "bindPose1.p[52]";
connectAttr "bindPose1.m[52]" "bindPose1.p[53]";
connectAttr "bindPose1.m[53]" "bindPose1.p[54]";
connectAttr "bindPose1.m[54]" "bindPose1.p[55]";
connectAttr "bindPose1.m[43]" "bindPose1.p[56]";
connectAttr "bindPose1.m[56]" "bindPose1.p[57]";
connectAttr "bindPose1.m[57]" "bindPose1.p[58]";
connectAttr "bindPose1.m[43]" "bindPose1.p[59]";
connectAttr "bindPose1.m[59]" "bindPose1.p[60]";
connectAttr "bindPose1.m[60]" "bindPose1.p[61]";
connectAttr "bindPose1.m[61]" "bindPose1.p[62]";
connectAttr "bindPose1.m[43]" "bindPose1.p[63]";
connectAttr "bindPose1.m[39]" "bindPose1.p[64]";
connectAttr "bindPose1.m[39]" "bindPose1.p[65]";
connectAttr "bindPose1.m[1]" "bindPose1.p[66]";
connectAttr "bindPose1.m[66]" "bindPose1.p[67]";
connectAttr "bindPose1.m[67]" "bindPose1.p[68]";
connectAttr "bindPose1.m[68]" "bindPose1.p[69]";
connectAttr "bindPose1.m[67]" "bindPose1.p[70]";
connectAttr "bindPose1.m[67]" "bindPose1.p[71]";
connectAttr "bindPose1.m[66]" "bindPose1.p[72]";
connectAttr "bindPose1.m[66]" "bindPose1.p[73]";
connectAttr "bindPose1.m[1]" "bindPose1.p[74]";
connectAttr "bindPose1.m[74]" "bindPose1.p[75]";
connectAttr "bindPose1.m[75]" "bindPose1.p[76]";
connectAttr "bindPose1.m[76]" "bindPose1.p[77]";
connectAttr "bindPose1.m[75]" "bindPose1.p[78]";
connectAttr "bindPose1.m[75]" "bindPose1.p[79]";
connectAttr "bindPose1.m[74]" "bindPose1.p[80]";
connectAttr "bindPose1.m[74]" "bindPose1.p[81]";
connectAttr "bindPose1.m[0]" "bindPose1.p[82]";
connectAttr "bindPose1.m[82]" "bindPose1.p[83]";
connectAttr "bindPose1.m[83]" "bindPose1.p[84]";
connectAttr "bindPose1.m[83]" "bindPose1.p[85]";
connectAttr "bindPose1.m[0]" "bindPose1.p[86]";
connectAttr "bindPose1.m[86]" "bindPose1.p[87]";
connectAttr "bindPose1.m[86]" "bindPose1.p[88]";
connectAttr "bindPose1.m[0]" "bindPose1.p[89]";
connectAttr "bindPose1.m[0]" "bindPose1.p[90]";
connectAttr "bindPose1.m[0]" "bindPose1.p[91]";
connectAttr "bindPose1.m[91]" "bindPose1.p[92]";
connectAttr "root.bps" "bindPose1.wm[0]";
connectAttr "pelvis.bps" "bindPose1.wm[1]";
connectAttr "spine_01.bps" "bindPose1.wm[2]";
connectAttr "spine_02.bps" "bindPose1.wm[3]";
connectAttr "spine_03.bps" "bindPose1.wm[4]";
connectAttr "spine_04.bps" "bindPose1.wm[5]";
connectAttr "spine_05.bps" "bindPose1.wm[6]";
connectAttr "neck_01.bps" "bindPose1.wm[7]";
connectAttr "neck_02.bps" "bindPose1.wm[8]";
connectAttr "head.bps" "bindPose1.wm[9]";
connectAttr "clavicle_l.bps" "bindPose1.wm[10]";
connectAttr "upperarm_l.bps" "bindPose1.wm[11]";
connectAttr "lowerarm_l.bps" "bindPose1.wm[12]";
connectAttr "lowerarm_twist_02_l.bps" "bindPose1.wm[13]";
connectAttr "lowerarm_twist_01_l.bps" "bindPose1.wm[14]";
connectAttr "hand_l.bps" "bindPose1.wm[15]";
connectAttr "middle_metacarpal_l.bps" "bindPose1.wm[16]";
connectAttr "middle_01_l.bps" "bindPose1.wm[17]";
connectAttr "middle_02_l.bps" "bindPose1.wm[18]";
connectAttr "middle_03_l.bps" "bindPose1.wm[19]";
connectAttr "pinky_metacarpal_l.bps" "bindPose1.wm[20]";
connectAttr "pinky_01_l.bps" "bindPose1.wm[21]";
connectAttr "pinky_02_l.bps" "bindPose1.wm[22]";
connectAttr "pinky_03_l.bps" "bindPose1.wm[23]";
connectAttr "ring_metacarpal_l.bps" "bindPose1.wm[24]";
connectAttr "ring_01_l.bps" "bindPose1.wm[25]";
connectAttr "ring_02_l.bps" "bindPose1.wm[26]";
connectAttr "ring_03_l.bps" "bindPose1.wm[27]";
connectAttr "thumb_01_l.bps" "bindPose1.wm[28]";
connectAttr "thumb_02_l.bps" "bindPose1.wm[29]";
connectAttr "thumb_03_l.bps" "bindPose1.wm[30]";
connectAttr "index_metacarpal_l.bps" "bindPose1.wm[31]";
connectAttr "index_01_l.bps" "bindPose1.wm[32]";
connectAttr "index_02_l.bps" "bindPose1.wm[33]";
connectAttr "index_03_l.bps" "bindPose1.wm[34]";
connectAttr "weapon_l.bps" "bindPose1.wm[35]";
connectAttr "upperarm_twist_01_l.bps" "bindPose1.wm[36]";
connectAttr "upperarm_twist_02_l.bps" "bindPose1.wm[37]";
connectAttr "clavicle_r.bps" "bindPose1.wm[38]";
connectAttr "upperarm_r.bps" "bindPose1.wm[39]";
connectAttr "lowerarm_r.bps" "bindPose1.wm[40]";
connectAttr "lowerarm_twist_02_r.bps" "bindPose1.wm[41]";
connectAttr "lowerarm_twist_01_r.bps" "bindPose1.wm[42]";
connectAttr "hand_r.bps" "bindPose1.wm[43]";
connectAttr "middle_metacarpal_r.bps" "bindPose1.wm[44]";
connectAttr "middle_01_r.bps" "bindPose1.wm[45]";
connectAttr "middle_02_r.bps" "bindPose1.wm[46]";
connectAttr "middle_03_r.bps" "bindPose1.wm[47]";
connectAttr "pinky_metacarpal_r.bps" "bindPose1.wm[48]";
connectAttr "pinky_01_r.bps" "bindPose1.wm[49]";
connectAttr "pinky_02_r.bps" "bindPose1.wm[50]";
connectAttr "pinky_03_r.bps" "bindPose1.wm[51]";
connectAttr "ring_metacarpal_r.bps" "bindPose1.wm[52]";
connectAttr "ring_01_r.bps" "bindPose1.wm[53]";
connectAttr "ring_02_r.bps" "bindPose1.wm[54]";
connectAttr "ring_03_r.bps" "bindPose1.wm[55]";
connectAttr "thumb_01_r.bps" "bindPose1.wm[56]";
connectAttr "thumb_02_r.bps" "bindPose1.wm[57]";
connectAttr "thumb_03_r.bps" "bindPose1.wm[58]";
connectAttr "index_metacarpal_r.bps" "bindPose1.wm[59]";
connectAttr "index_01_r.bps" "bindPose1.wm[60]";
connectAttr "index_02_r.bps" "bindPose1.wm[61]";
connectAttr "index_03_r.bps" "bindPose1.wm[62]";
connectAttr "weapon_r.bps" "bindPose1.wm[63]";
connectAttr "upperarm_twist_01_r.bps" "bindPose1.wm[64]";
connectAttr "upperarm_twist_02_r.bps" "bindPose1.wm[65]";
connectAttr "thigh_r.bps" "bindPose1.wm[66]";
connectAttr "calf_r.bps" "bindPose1.wm[67]";
connectAttr "foot_r.bps" "bindPose1.wm[68]";
connectAttr "ball_r.bps" "bindPose1.wm[69]";
connectAttr "calf_twist_02_r.bps" "bindPose1.wm[70]";
connectAttr "calf_twist_01_r.bps" "bindPose1.wm[71]";
connectAttr "thigh_twist_01_r.bps" "bindPose1.wm[72]";
connectAttr "thigh_twist_02_r.bps" "bindPose1.wm[73]";
connectAttr "thigh_l.bps" "bindPose1.wm[74]";
connectAttr "calf_l.bps" "bindPose1.wm[75]";
connectAttr "foot_l.bps" "bindPose1.wm[76]";
connectAttr "ball_l.bps" "bindPose1.wm[77]";
connectAttr "calf_twist_02_l.bps" "bindPose1.wm[78]";
connectAttr "calf_twist_01_l.bps" "bindPose1.wm[79]";
connectAttr "thigh_twist_01_l.bps" "bindPose1.wm[80]";
connectAttr "thigh_twist_02_l.bps" "bindPose1.wm[81]";
connectAttr "ik_hand_root.bps" "bindPose1.wm[82]";
connectAttr "ik_hand_gun.bps" "bindPose1.wm[83]";
connectAttr "ik_hand_r.bps" "bindPose1.wm[84]";
connectAttr "ik_hand_l.bps" "bindPose1.wm[85]";
connectAttr "ik_foot_root.bps" "bindPose1.wm[86]";
connectAttr "ik_foot_l.bps" "bindPose1.wm[87]";
connectAttr "ik_foot_r.bps" "bindPose1.wm[88]";
connectAttr "interaction.bps" "bindPose1.wm[89]";
connectAttr "center_of_mass.bps" "bindPose1.wm[90]";
connectAttr "camera_root.bps" "bindPose1.wm[91]";
connectAttr "camera_bone.bps" "bindPose1.wm[92]";
connectAttr "defaultRenderLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "CapeShape.iog" ":initialShadingGroup.dsm" -na;
// End of MainHero_Cape.ma
