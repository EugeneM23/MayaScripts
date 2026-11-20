//Maya ASCII 2027 scene
//Name: MainHero_Helmet.ma
//Last modified: Fri, Nov 20, 2026 05:41:00 PM
//Codeset: 1252
requires maya "2027";
currentUnit -l centimeter -a degree -t ntsc;
fileInfo "application" "maya";
fileInfo "product" "Maya 2027";
fileInfo "version" "2027";
fileInfo "cutIdentifier" "202607171511-52c21617ee";
fileInfo "osv" "Windows 11 Home v2009 (Build: 26200)";
fileInfo "UUID" "0FE910B6-4FDC-061D-FFA5-97B60795BAB0";
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
createNode transform -n "MainHero_Helmet";
	rename -uid "8B19FDD0-41D4-38BE-942F-8B9B0A285F6F";
createNode transform -n "Helmet" -p "MainHero_Helmet";
	rename -uid "96185B14-483F-8F11-A2C2-14B33C604446";
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
createNode mesh -n "HelmetShape" -p "Helmet";
	rename -uid "26E2009B-4CDB-8A37-A2CE-44961326F7E9";
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
createNode mesh -n "HelmetShapeOrig" -p "Helmet";
	rename -uid "F89F5FE5-47DF-0C19-52B3-83A7781D283A";
	setAttr -k off ".v";
	setAttr ".io" yes;
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr -s 2472 ".uvst[0].uvsp";
	setAttr ".uvst[0].uvsp[0:249]" -type "float2" 0.40201157 0.22164446 0.40372145
		 0.22023332 0.40742946 0.22317398 0.40896422 0.22343409 0.41458803 0.22724509 0.406057
		 0.22327441 0.40895128 0.22498941 0.40597454 0.22473443 0.40448621 0.22332078 0.40418753
		 0.22257912 0.40368283 0.22260237 0.40205029 0.22222126 0.40186745 0.22362202 0.40111548
		 0.22341603 0.40031728 0.22342122 0.39994392 0.22239888 0.40007266 0.22449756 0.39912501
		 0.22375339 0.39680237 0.22273624 0.39701092 0.22688204 0.39606592 0.22140241 0.39772418
		 0.22185045 0.39723238 0.2209183 0.39722466 0.22039551 0.39847609 0.22092342 0.39833447
		 0.2201767 0.39724523 0.21931922 0.40122885 0.21878099 0.40072671 0.21981096 0.40348968
		 0.21923423 0.40374976 0.21842307 0.41549185 0.2262305 0.41674331 0.22532159 0.41766775
		 0.22613525 0.41765746 0.22454649 0.41746691 0.22455418 0.41866943 0.22273368 0.41896042
		 0.22308129 0.41888317 0.2216419 0.41818792 0.22232425 0.41556394 0.220617 0.41326702
		 0.22114229 0.41508499 0.22296798 0.40311116 0.21539742 0.40708184 0.2158609 0.40987572
		 0.21768665 0.40747839 0.21573734 0.40398666 0.21200097 0.40663639 0.21425408 0.4134447
		 0.21879131 0.40909806 0.21493387 0.40510681 0.21159667 0.41943422 0.22065043 0.40736511
		 0.21197784 0.40798312 0.21144992 0.41893211 0.21935523 0.41951662 0.21987283 0.41979989
		 0.21836388 0.41385415 0.21467644 0.40881482 0.21107912 0.41239667 0.21318549 0.41071004
		 0.21091944 0.41268763 0.21258807 0.41138473 0.21132886 0.41695189 0.21572447 0.41259235
		 0.21140611 0.4208582 0.21731323 0.41306102 0.21127224 0.41514939 0.21262413 0.41294
		 0.20859158 0.41717336 0.21186191 0.41447729 0.2063024 0.41267222 0.20646209 0.41134089
		 0.20771611 0.41234776 0.20387673 0.41018218 0.20801997 0.41138729 0.20924312 0.4096337
		 0.20797873 0.41006371 0.20459002 0.40752736 0.20274633 0.40689129 0.20466983 0.40743205
		 0.20841396 0.40652823 0.20885944 0.40476948 0.2048707 0.40468448 0.2071625 0.40549818
		 0.20910919 0.40383473 0.20838052 0.40085027 0.20828265 0.4016434 0.21057439 0.40094557
		 0.21265244 0.40015757 0.21267563 0.40073183 0.21087307 0.39902976 0.2119984 0.39895505
		 0.21246964 0.39888036 0.21430814 0.40034559 0.21344554 0.39903748 0.214679 0.39778599
		 0.21534848 0.40110263 0.21607721 0.39931303 0.2170248 0.3965371 0.21543604 0.39626417
		 0.21679568 0.39878765 0.21809858 0.40076786 0.21792096 0.40239528 0.21657681 0.39652938
		 0.2178334 0.39258444 0.21800077 0.39345998 0.21920073 0.39098021 0.21878356 0.38993478
		 0.2167905 0.38917771 0.21654075 0.39055794 0.21601802 0.39242736 0.21279407 0.38894853
		 0.21398628 0.38827643 0.21401203 0.38634774 0.21430814 0.38898715 0.21742135 0.39059138
		 0.21883506 0.38962835 0.21907461 0.39107034 0.22196889 0.39204368 0.22191483 0.39212096
		 0.22376108 0.38809878 0.22577989 0.38976482 0.22818244 0.38697863 0.22769576 0.38592288
		 0.22623312 0.38254443 0.2309866 0.38487479 0.22579795 0.38680866 0.22247362 0.38944292
		 0.22151566 0.38706875 0.22081012 0.38684469 0.21757329 0.38454783 0.21899217 0.38455296
		 0.21627808 0.37809998 0.21451676 0.37779868 0.21290219 0.37765187 0.21443951 0.37416273
		 0.21726179 0.37161604 0.21704286 0.3723782 0.21854925 0.36830196 0.22161615 0.36779469
		 0.21986508 0.36203179 0.22677898 0.35978118 0.22664511 0.35987645 0.22495592 0.35747913
		 0.22620225 0.35556847 0.22322297 0.35972196 0.21361041 0.35547578 0.21680593 0.35555044
		 0.2098766 0.35288012 0.21245414 0.34966907 0.21020103 0.35242951 0.2084474 0.35028964
		 0.20679682 0.35593668 0.20471621 0.35199693 0.20271802 0.34868801 0.20072496 0.35289818
		 0.19958937 0.34866223 0.19882202 0.35090768 0.19702458 0.34699878 0.19401699 0.3491824
		 0.1941303 0.34432849 0.1915012 0.34369501 0.19206768 0.34350449 0.19687784 0.33944881
		 0.1949569 0.34013379 0.19044799 0.33492193 0.19212437 0.33721885 0.18918622 0.34038097
		 0.18963689 0.33669096 0.18817937 0.3329649 0.18783951 0.33233917 0.18649793 0.33530301
		 0.18718547 0.33787289 0.1882953 0.33400008 0.18598807 0.33246794 0.18615031 0.32782257
		 0.18362933 0.33366272 0.18234444 0.3376154 0.18387651 0.33372968 0.18216157 0.32637283
		 0.17943722 0.3263883 0.17928529 0.33085594 0.17739004 0.32435915 0.17510855 0.32155496
		 0.17584503 0.31940225 0.17317218 0.31668302 0.17550772 0.31567878 0.17185634 0.31322992
		 0.17409408 0.30734342 0.17089069 0.31135014 0.16909593 0.30551517 0.16664445 0.31163597
		 0.16878176 0.3139329 0.1696856 0.31440926 0.17032933 0.31816107 0.17150611 0.31841344
		 0.17196447 0.32431796 0.17408115 0.32260302 0.17410433 0.33115208 0.17677206 0.32439005
		 0.17368716 0.33131173 0.1763832 0.33641025 0.17871106 0.33623001 0.17827845 0.34082389
		 0.18010157 0.34052518 0.18036163 0.3370077 0.17977452 0.34268308 0.18195295 0.3438392
		 0.18151784 0.34837899 0.18274611 0.34760389 0.18348515 0.35305268 0.18429887 0.35225442
		 0.18292636 0.34847686 0.18197358 0.34479198 0.18073243 0.34421259 0.18118048 0.3417818
		 0.17973334 0.33777249 0.17786646 0.34259552 0.17616433 0.33839303 0.17500561 0.33407986
		 0.17371809 0.33842394 0.16939461 0.34178433 0.17000234 0.33554766 0.16560161 0.33964452
		 0.16305232 0.33568156 0.1620326 0.33303183 0.16452271 0.33014011 0.17174304 0.3286646
		 0.17459619 0.33334085 0.17653257 0.32654533 0.16999722 0.32284763 0.17223489 0.31823316
		 0.17123061 0.31843662 0.17066926 0.31986058 0.1667707 0.32343471 0.16608053 0.32356861
		 0.16429859 0.32632652 0.16501963 0.3303358 0.1643939 0.32765517 0.16070902 0.33095378
		 0.16139144 0.33173147 0.15744907 0.33686861 0.15809798 0.33235717 0.15474528 0.3282088
		 0.15461397 0.332728 0.15036261 0.32623893 0.15060723 0.32852039 0.14789057 0.33230311
		 0.14786226;
	setAttr ".uvst[0].uvsp[250:499]" 0.33525151 0.15025187 0.33616564 0.14813006
		 0.33882567 0.14867854 0.3390986 0.14645886 0.34303066 0.14739358 0.3435972 0.1465258
		 0.34503663 0.14739871 0.34573701 0.14699966 0.34654042 0.14817125 0.34528899 0.14783907
		 0.34556448 0.14838243 0.34487954 0.14892316 0.3453379 0.15019524 0.35258144 0.15159345
		 0.34793869 0.14990687 0.34715071 0.14873779 0.3492468 0.14907253 0.34760389 0.14839274
		 0.34937811 0.14877379 0.35078409 0.149827 0.3524707 0.1499635 0.3517909 0.14922959
		 0.35476246 0.15020812 0.35313505 0.14861929 0.35685083 0.15069222 0.35789886 0.15018493
		 0.35990736 0.14765882 0.35081756 0.14438599 0.35445607 0.1445843 0.34365124 0.14188564
		 0.35327154 0.14389676 0.36268583 0.14586663 0.36370555 0.14641511 0.37037748 0.14787513
		 0.36419994 0.1490339 0.37101603 0.15399855 0.3677097 0.15347326 0.36375445 0.1524381
		 0.35929197 0.15224236 0.36313644 0.15349126 0.36175883 0.15349126 0.35767224 0.15187931
		 0.36259311 0.15442598 0.35483202 0.1507901 0.35676327 0.1526956 0.36528403 0.15636498
		 0.36419737 0.1546011 0.36842558 0.15635467 0.36572435 0.15481997 0.36788481 0.1553247
		 0.36836377 0.15589893 0.37226492 0.15775549 0.37302199 0.15738469 0.3739773 0.15825504
		 0.36971569 0.15873915 0.37550434 0.15982324 0.37716267 0.15846622 0.38366458 0.16115201
		 0.38260111 0.15887821 0.38389379 0.15936232 0.37825698 0.15643191 0.38144746 0.15326464
		 0.3778888 0.14901328 0.37946984 0.14798844 0.3798947 0.14797556 0.37868965 0.14588463
		 0.37870762 0.14479798 0.38032991 0.14673185 0.37643906 0.13867712 0.37642875 0.14101267
		 0.37198424 0.13467038 0.37382799 0.14055175 0.37148988 0.14455849 0.36710972 0.14116716
		 0.36819637 0.13387215 0.36775094 0.13242757 0.36891997 0.13317943 0.36907962 0.13090312
		 0.37234735 0.13163441 0.37005818 0.13410127 0.3733387 0.13247389 0.3728649 0.130916
		 0.37202805 0.12343299 0.37050623 0.1290105 0.37057829 0.12131119 0.3735061 0.11754906
		 0.36965901 0.1189447 0.36876032 0.12189829 0.36871657 0.11688727 0.36683166 0.12316519
		 0.36696294 0.11651134 0.36877838 0.11509508 0.36618012 0.11062998 0.36906937 0.11452085
		 0.36914662 0.11266685 0.36876544 0.11077678 0.3694247 0.10885835 0.36459908 0.10351002
		 0.36727458 0.10285342 0.36498019 0.10212469 0.3609966 0.10088354 0.362194 0.099191725
		 0.35898551 0.096794367 0.35408267 0.097157478 0.35306296 0.10121572 0.35172909 0.096315384
		 0.35395133 0.093840837 0.34373108 0.092337012 0.34705287 0.088731945 0.35763106 0.092391074
		 0.35959837 0.093863964 0.35816154 0.091845155 0.35773405 0.085935473 0.35634869 0.086463392
		 0.35542685 0.077015638 0.35543713 0.075934112 0.35381743 0.071618378 0.3504802 0.069831312
		 0.3516055 0.066882849 0.3522132 0.064781666 0.35002702 0.061967194 0.34942445 0.06174314
		 0.34759876 0.058096945 0.34666404 0.061776638 0.34435424 0.056134701 0.34035262 0.055990517
		 0.33646694 0.045335054 0.34211656 0.049975276 0.33882824 0.044106781 0.33325842 0.042798698
		 0.3370257 0.041642487 0.33742741 0.041593552 0.33429363 0.03720057 0.331716 0.036603153
		 0.32982594 0.031429946 0.3304671 0.026756287 0.32807493 0.030587912 0.32109663 0.031048834
		 0.3234064 0.032462537 0.31768471 0.034365475 0.31774905 0.035192072 0.3178727 0.036425531
		 0.3187868 0.037357688 0.32004857 0.03672421 0.3237077 0.034422159 0.32611275 0.034965456
		 0.327117 0.035089076 0.32712731 0.033065081 0.32871097 0.033950865 0.32813931 0.035936236
		 0.33010921 0.037777364 0.32750067 0.040053725 0.32655567 0.036734462 0.32575226 0.039448559
		 0.32369739 0.041580677 0.32559776 0.037288129 0.32291973 0.037769675 0.32320556 0.041155815
		 0.31910613 0.03911382 0.31911126 0.038346469 0.3166315 0.036502719 0.31230548 0.040262282
		 0.31146345 0.034772336 0.30373579 0.034216166 0.31423414 0.032812774 0.3150942 0.030173361
		 0.31260416 0.030098677 0.30772194 0.029920995 0.30185348 0.030690908 0.29911104 0.028744221
		 0.29652572 0.031275451 0.29622445 0.031090081 0.29374468 0.033361256 0.29031992 0.032944083
		 0.29563475 0.028620601 0.28834745 0.031360388 0.29025039 0.029048085 0.28574154 0.029037774
		 0.28137428 0.029879808 0.28489175 0.032962084 0.28021038 0.032575846 0.28078973 0.039119005
		 0.27948678 0.035009205 0.2782611 0.032135487 0.27804992 0.033132076 0.27395049 0.040326655
		 0.27364406 0.032807589 0.27306208 0.031435132 0.28000954 0.030623972 0.28073567 0.029771686
		 0.26933092 0.033698559 0.26892921 0.03234154 0.26631039 0.03414917 0.2679584 0.032501161
		 0.266846 0.032287419 0.26440227 0.031419635 0.26315856 0.033219576 0.26233199 0.02847898
		 0.26128909 0.029686689 0.25647378 0.033332884 0.25621885 0.031476319 0.25505495 0.02794081
		 0.25476915 0.029403389 0.2508834 0.021147907 0.25940931 0.023158967 0.25800851 0.019322217
		 0.25011608 0.019783139 0.25069803 0.021204531 0.24856591 0.0214414 0.24693075 0.018747985
		 0.24830067 0.017004669 0.24912724 0.016778052 0.24714963 0.015024483 0.24823888 0.014936924
		 0.24598315 0.013713777 0.24517459 0.014620185 0.24517202 0.011805713 0.25185421 0.013332665
		 0.25217867 0.012601376 0.25292543 0.014164388 0.25323442 0.013695776 0.25402498 0.014383316
		 0.25588155 0.015923142 0.25487727 0.016028762 0.25782827 0.018426061 0.26012003 0.02301991
		 0.25407389 0.013507783 0.25432107 0.012892365 0.25293317 0.011937022 0.25334001 0.0096452236
		 0.24935642 0.0085766315 0.2479376 0.0079277158 0.24720371 0.007832408 0.24659859
		 0.0081182718 0.24417548 0.015009046 0.24456431 0.018124819 0.24362701 0.01578927
		 0.2428648 0.015992701 0.24176784 0.017135978 0.2431532 0.019064665 0.24338496 0.020431995
		 0.24325104 0.02227056 0.24950323 0.025978625 0.24736594 0.026109934 0.24843715 0.028515041
		 0.25034526 0.027842939 0.25150403 0.028033495 0.25010577 0.030464292 0.25295886 0.032089174
		 0.25373656 0.030593038;
	setAttr ".uvst[0].uvsp[500:749]" 0.25215805 0.028504729 0.25029886 0.023833632
		 0.25471506 0.029854 0.25348422 0.031934619 0.25341466 0.033168077 0.25509101 0.034738839
		 0.25358203 0.038910389 0.25287393 0.041542113 0.25163791 0.039124131 0.25279409 0.038544774
		 0.25180012 0.037100136 0.25052807 0.039937854 0.25177181 0.042324901 0.24659084 0.048940122
		 0.25678024 0.043720543 0.26023334 0.042093158 0.26212853 0.041464806 0.26139465 0.04290688
		 0.2663413 0.041173816 0.26143071 0.043313682 0.25863683 0.048324704 0.25363097 0.051643908
		 0.25074178 0.064060628 0.26161611 0.057301223 0.25874239 0.064869225 0.25838962 0.068785846
		 0.24731185 0.068834782 0.25616479 0.074208856 0.25896898 0.072241485 0.25702745 0.077916861
		 0.25444469 0.082585394 0.25866514 0.080986321 0.25637853 0.087552607 0.25172547 0.087490797
		 0.25242844 0.082366526 0.25019333 0.087485671 0.24774702 0.092488885 0.24625868 0.092092395
		 0.24878994 0.086808443 0.24625868 0.089414358 0.2429266 0.091304421 0.23987262 0.096006393
		 0.2421927 0.097409785 0.23944001 0.10061568 0.23863146 0.096318007 0.23812933 0.093307793
		 0.24103652 0.10384995 0.24098761 0.106152 0.24346992 0.10623443 0.24396691 0.10196757
		 0.24760799 0.097051859 0.24752302 0.099817455 0.24585438 0.10473317 0.24894445 0.10317528
		 0.24862513 0.10482073 0.25185165 0.10070843 0.25003108 0.099230349 0.2535975 0.093145549
		 0.25166106 0.09229064 0.25504982 0.093668282 0.25823513 0.093155861 0.25742656 0.094891429
		 0.2587398 0.093212485 0.25978786 0.094000459 0.2576094 0.097865582 0.25973117 0.097293913
		 0.25776905 0.10193157 0.25549272 0.10124147 0.25397858 0.10059512 0.25393999 0.10008782
		 0.25028858 0.10352033 0.25016242 0.10429025 0.25169456 0.10528678 0.24882081 0.10584557
		 0.24419093 0.11018962 0.24395661 0.10910296 0.24337465 0.1106686 0.24900624 0.11175525
		 0.24664494 0.11750525 0.25408933 0.11510539 0.2484732 0.12014729 0.25678796 0.11954987
		 0.25173834 0.12456858 0.25768405 0.12438577 0.255588 0.12792897 0.25702229 0.12681913
		 0.26002994 0.12603378 0.25992945 0.13034952 0.26048055 0.12737536 0.26382032 0.12318063
		 0.26358086 0.12712818 0.26234999 0.13112718 0.26548123 0.12991691 0.26712671 0.12210172
		 0.26753095 0.12736505 0.2637611 0.13420945 0.26428643 0.1373021 0.26255602 0.13599914
		 0.26638249 0.13991058 0.2675181 0.14226931 0.26341093 0.138587 0.26141527 0.13800764
		 0.25852093 0.13226789 0.25983936 0.13154948 0.25758106 0.13056064 0.25677764 0.13069457
		 0.26249936 0.14093548 0.26710093 0.14577907 0.27187502 0.14492929 0.27224582 0.14191651
		 0.27342519 0.14035863 0.27436507 0.14329934 0.27587402 0.14027107 0.27407411 0.13960928
		 0.27561653 0.13576734 0.27352563 0.13363266 0.27651519 0.13173485 0.27683964 0.13230652
		 0.27588433 0.1362772 0.27750659 0.13727117 0.27674699 0.1382162 0.2779263 0.13716304
		 0.27955374 0.13399577 0.27948937 0.13046801 0.28006873 0.13021302 0.28138977 0.12615997
		 0.28166267 0.1285882 0.28318709 0.12808347 0.28183267 0.13346016 0.28510034 0.13116837
		 0.28478876 0.13737935 0.28900665 0.13604546 0.27849025 0.13979214 0.29132932 0.1358704
		 0.29242373 0.13507211 0.28951392 0.13006109 0.29451981 0.13104737 0.29560903 0.12562954
		 0.29687592 0.1291315 0.2980012 0.12614453 0.29910076 0.12781054 0.30065346 0.12274802
		 0.29930159 0.12175667 0.30115563 0.11880052 0.30340877 0.11848891 0.30300191 0.12035072
		 0.30587563 0.11882627 0.30158567 0.12375492 0.30704212 0.11954212 0.30363023 0.12440377
		 0.30416325 0.12624234 0.30093673 0.12688613 0.30105004 0.12941736 0.2998372 0.12744749
		 0.29875568 0.13090062 0.29785442 0.13237345 0.29875055 0.1319924 0.29783127 0.1334756
		 0.30097795 0.13138467 0.30227575 0.13247389 0.29827932 0.13402152 0.30155221 0.1342352
		 0.30274954 0.13376141 0.30327228 0.13358629 0.30445164 0.1332258 0.30692109 0.13585496
		 0.30561814 0.13554597 0.30698806 0.13793552 0.30780432 0.1378969 0.30729961 0.13863593
		 0.3027367 0.13588327 0.30794853 0.14026332 0.30538377 0.13886255 0.29894367 0.13587809
		 0.2965695 0.13608408 0.30254102 0.13979983 0.30214185 0.14283067 0.29739866 0.14165646
		 0.29338935 0.13715529 0.292622 0.13784802 0.29153532 0.13872606 0.29024526 0.13785315
		 0.28815949 0.13741797 0.28754404 0.13725317 0.28699043 0.13923335 0.2786628 0.14226156
		 0.27842331 0.14301348 0.28602734 0.13986939 0.28690803 0.14501429 0.27865246 0.14595932
		 0.2755805 0.14481598 0.28706253 0.15555131 0.27743709 0.14896178 0.27654868 0.14278173
		 0.27177975 0.15145445 0.27751175 0.15586287 0.28267723 0.15950906 0.27150163 0.15850222
		 0.28187126 0.16386861 0.28115281 0.16533893 0.27748343 0.16327894 0.2811065 0.16570461
		 0.26749489 0.15866709 0.26953432 0.16119319 0.26520574 0.17314899 0.2662254 0.16269952
		 0.26605031 0.15824473 0.26397228 0.16324031 0.26639023 0.15427411 0.2680099 0.14953345
		 0.26913261 0.1471644 0.26363236 0.16444284 0.26321778 0.17422283 0.26273882 0.17537642
		 0.26372504 0.17548454 0.26279035 0.17906123 0.26216719 0.17990839 0.26464435 0.18801975
		 0.26356027 0.18728077 0.26496106 0.19287622 0.266864 0.19106865 0.26722971 0.19297153
		 0.26763394 0.19438261 0.26859185 0.19790274 0.26653442 0.19870615 0.26867169 0.20109057
		 0.26899871 0.2028107 0.27020642 0.2018373 0.27121583 0.2056458 0.26990515 0.20628697
		 0.2728484 0.21169972 0.27241063 0.21212971 0.27875292 0.2200557 0.27997088 0.21796215
		 0.28156739 0.22166502 0.28343946 0.21978527 0.2834034 0.21849775 0.28714749 0.22193283
		 0.28669944 0.22320229 0.29078856 0.2257387 0.29209414 0.22116804 0.28924614 0.21434426
		 0.29903126 0.21497256 0.29487258 0.2117306 0.28822899 0.20861995 0.27995029 0.2106027
		 0.27762249 0.21411765 0.27485687 0.20955473 0.27464578 0.211146 0.27802932 0.21530211;
	setAttr ".uvst[0].uvsp[750:999]" 0.27730316 0.21531761 0.27231279 0.20525956
		 0.27171022 0.20539343 0.2709094 0.20202792 0.27380112 0.20521581 0.27362603 0.20251453
		 0.27350503 0.20194805 0.27623194 0.20240128 0.27410758 0.20142531 0.27792376 0.20244503
		 0.27939409 0.20513594 0.2839905 0.20484239 0.28629518 0.20548356 0.28588831 0.20500457
		 0.29450178 0.21002591 0.30013335 0.21311593 0.29369578 0.20907575 0.29726994 0.21044052
		 0.30153158 0.21213746 0.29960802 0.2109735 0.29942521 0.21042246 0.29796517 0.20800197
		 0.29636607 0.2086457 0.29286921 0.20657027 0.29443741 0.20864058 0.28819299 0.20551962
		 0.29049504 0.20732212 0.28755951 0.20382524 0.28288066 0.20319444 0.28028247 0.20275921
		 0.2773006 0.20122707 0.281073 0.20064259 0.27456591 0.19895333 0.2709789 0.20139188
		 0.26979184 0.19862628 0.27747828 0.19560575 0.28120691 0.20039022 0.28124037 0.19660228
		 0.28266951 0.19577575 0.2860119 0.19794905 0.28758782 0.20358062 0.29167956 0.20558393
		 0.29155079 0.20093089 0.30065608 0.2057308 0.29402536 0.20011467 0.28722474 0.1964401
		 0.29123148 0.19559288 0.28824186 0.19385219 0.28257424 0.19329602 0.28488407 0.19242561
		 0.27743709 0.18908322 0.28522655 0.19209862 0.2824223 0.18906778 0.28535786 0.18672973
		 0.28512868 0.18254268 0.27977517 0.1819942 0.27696326 0.18587476 0.27302605 0.18229032
		 0.26596019 0.18441987 0.26684856 0.18509972 0.26664773 0.18614256 0.26724771 0.18713909
		 0.27548262 0.19056904 0.27014205 0.19097847 0.27472556 0.19316208 0.27806023 0.19219387
		 0.27768683 0.19119215 0.27948678 0.1945371 0.27413073 0.18796825 0.26550698 0.18072212
		 0.27056432 0.18045694 0.2658855 0.17953503 0.26643145 0.17828101 0.27415392 0.1788733
		 0.2680099 0.17646563 0.26613787 0.17573947 0.26838845 0.17420477 0.27175915 0.17000484
		 0.27681395 0.1734606 0.2782276 0.17607421 0.2793529 0.17842007 0.28405744 0.17493093
		 0.28522655 0.17787671 0.2766079 0.18123716 0.28836548 0.17868787 0.28743333 0.18431944
		 0.29052335 0.18091786 0.29291552 0.18156415 0.29286405 0.1756236 0.29590258 0.17701411
		 0.29514551 0.17250782 0.29792911 0.17506999 0.29950505 0.17406058 0.30314872 0.17792308
		 0.3053349 0.17669737 0.30747217 0.18060887 0.30841205 0.17773771 0.30733052 0.17646307
		 0.31403846 0.17931622 0.3142007 0.17910761 0.32024169 0.18176758 0.32056355 0.18138391
		 0.31443247 0.17889386 0.30933392 0.17666388 0.307758 0.17629313 0.30767044 0.17583215
		 0.30175817 0.17380822 0.30179167 0.17352235 0.3066842 0.17207009 0.31297755 0.17716861
		 0.30285513 0.16971648 0.29906985 0.17080313 0.296433 0.16745305 0.29696348 0.16657758
		 0.30150068 0.16639984 0.29749912 0.16471064 0.29442194 0.16251934 0.30005351 0.16414154
		 0.29474124 0.16094595 0.29498586 0.16057253 0.29058 0.15778124 0.29041004 0.15817267
		 0.285878 0.15685165 0.29114652 0.16126525 0.28801012 0.16259915 0.29192415 0.16461539
		 0.28861526 0.1659466 0.2914452 0.16775948 0.29022977 0.16883326 0.28565395 0.16722906
		 0.29010618 0.16927361 0.29013452 0.16972679 0.28576985 0.1677826 0.28707796 0.16951048
		 0.28067389 0.1664024 0.28376648 0.17170441 0.27747568 0.16886413 0.28737152 0.17246664
		 0.2927559 0.17150867 0.28998002 0.17401934 0.29438588 0.17119968 0.29642528 0.17187947
		 0.29623732 0.17126149 0.29342797 0.17056364 0.29515579 0.16876376 0.28760329 0.1547659
		 0.29362109 0.15820098 0.29526654 0.16027641 0.29844409 0.16136825 0.29909563 0.16270214
		 0.30087236 0.16381192 0.30046809 0.16388404 0.30576232 0.16637665 0.30457523 0.16466945
		 0.31042057 0.16703844 0.31014246 0.16482651 0.3151097 0.1659801 0.31328401 0.16845477
		 0.3125295 0.16175711 0.31758684 0.16477758 0.31697914 0.16012454 0.31341532 0.15755463
		 0.31814563 0.15613836 0.31725985 0.15387493 0.31264022 0.15322089 0.30977422 0.15542507
		 0.30879316 0.15309471 0.30542758 0.15395987 0.30606622 0.15587831 0.30206206 0.15909964
		 0.30237615 0.15221149 0.30655289 0.14991713 0.30571085 0.14904678 0.31158704 0.14463836
		 0.31068063 0.14771807 0.31061625 0.14982444 0.31355438 0.14903903 0.31431913 0.1454469
		 0.31725985 0.14670604 0.31786495 0.14610869 0.31593364 0.14340746 0.31085056 0.14245468
		 0.30496666 0.14168221 0.30716828 0.14104354 0.31002659 0.14020151 0.31271234 0.14116716
		 0.31017849 0.13996726 0.31249088 0.13984102 0.30985406 0.13819045 0.30783266 0.13847631
		 0.31077334 0.13491249 0.31543416 0.13777846 0.31561956 0.13759047 0.3139638 0.13536823
		 0.31215355 0.13349104 0.31346679 0.13402665 0.31442213 0.13511842 0.31835163 0.13702911
		 0.3186658 0.13670725 0.31495777 0.13472706 0.31989661 0.13681024 0.31890786 0.13476568
		 0.31519207 0.13348335 0.3126325 0.13252026 0.31130382 0.13198984 0.31091756 0.13120186
		 0.31038707 0.13165247 0.31038707 0.13107824 0.3135801 0.13058639 0.31453031 0.13162154
		 0.31759456 0.12961823 0.31851128 0.1286757 0.32188201 0.12812728 0.3253454 0.12671876
		 0.31800658 0.12757367 0.3253634 0.12515056 0.31755593 0.12731355 0.32452911 0.12221241
		 0.32765263 0.12429821 0.32814187 0.12232828 0.33167222 0.12282789 0.32827836 0.12653846
		 0.33200699 0.12460464 0.33614507 0.12472051 0.33501717 0.12210172 0.33102334 0.11721689
		 0.33922994 0.12075239 0.33826432 0.11754906 0.34545633 0.10993987 0.33436573 0.1134342
		 0.34730008 0.10484391 0.35262519 0.10729533 0.35152054 0.10184914 0.35288528 0.10678291
		 0.35190162 0.10161221 0.3533076 0.10499322 0.35629204 0.11279815 0.35553241 0.11318952
		 0.35884133 0.11498952 0.35513845 0.11339039 0.35756928 0.11522895 0.3616893 0.1170032
		 0.35924044 0.11778337 0.35694352 0.11757737 0.35550925 0.11817735 0.35391274 0.11818767
		 0.35210761 0.11683321 0.34922618 0.11724776 0.35237545 0.11621267 0.34949139 0.1201061;
	setAttr ".uvst[0].uvsp[1000:1249]" 0.33753815 0.12196523 0.33762568 0.12163049
		 0.33797333 0.1233815 0.338442 0.12328881 0.337327 0.12447846 0.34129512 0.12564498
		 0.34183589 0.12281758 0.34667692 0.12131631 0.34536362 0.12126994 0.34479198 0.12157124
		 0.34143418 0.12252659 0.35109565 0.12619859 0.3569693 0.12762773 0.36246696 0.1303212
		 0.367975 0.12845945 0.36748824 0.13050658 0.36937833 0.12903881 0.369968 0.13091862
		 0.3685827 0.12642777 0.36889678 0.12568617 0.36847192 0.12498313 0.36632952 0.12370598
		 0.36470723 0.12123394 0.36395791 0.12203735 0.36328068 0.11971724 0.36367205 0.1189602
		 0.3636798 0.1152702 0.36338109 0.11257929 0.36431068 0.11091322 0.35964218 0.11411399
		 0.36282229 0.1408273 0.36560592 0.14323491 0.35663453 0.14175689 0.35392559 0.14162815
		 0.35796064 0.14268649 0.35627401 0.14276111 0.35804048 0.14368814 0.36523256 0.14429325
		 0.37099543 0.14555246 0.37178084 0.14626575 0.37637213 0.14665198 0.37626398 0.14577389
		 0.3763206 0.14479023 0.35481143 0.14294398 0.34633958 0.1406213 0.34737217 0.14018869
		 0.33950287 0.13923591 0.33935353 0.13982046 0.33602917 0.13934922 0.33638194 0.1372841
		 0.33929688 0.13739741 0.34410703 0.13767028 0.33887714 0.13044477 0.34554389 0.13011003
		 0.33503008 0.12887663 0.3341597 0.12524325 0.331801 0.12602091 0.32943198 0.13275975
		 0.32774532 0.12748098 0.3253943 0.13625664 0.32132322 0.13119155 0.32166055 0.13744885
		 0.33155635 0.13752866 0.32974356 0.13874668 0.33248854 0.13972771 0.33597767 0.1408118
		 0.33837762 0.13999814 0.33921966 0.14147878 0.33561459 0.14416969 0.33085337 0.14192683
		 0.33072463 0.1406213 0.32506987 0.13983595 0.32885259 0.13943678 0.32345533 0.13831151
		 0.32152662 0.13915348 0.3218511 0.1431371 0.3163251 0.14180326 0.32267764 0.14507091
		 0.33103621 0.14506578 0.34692922 0.14418256 0.3455362 0.14085561 0.35418051 0.13319749
		 0.35005793 0.13835788 0.34744167 0.13982821 0.35877952 0.13804883 0.34138265 0.097718775
		 0.33733729 0.1025573 0.33103365 0.10667729 0.32742858 0.10794681 0.32355061 0.11094928
		 0.32723546 0.11711901 0.32479435 0.1163671 0.3204065 0.11322302 0.31937134 0.11164969
		 0.3160547 0.11498952 0.3170847 0.11638516 0.31272778 0.11857134 0.31324536 0.11966062
		 0.31004202 0.12311625 0.31093043 0.12381148 0.31444791 0.12033272 0.3132093 0.12282014
		 0.31272006 0.12544668 0.31007293 0.1292088 0.30823952 0.12826633 0.30672538 0.13103706
		 0.30374095 0.13152111 0.30638552 0.12501407 0.30395985 0.12915987 0.3085717 0.12048972
		 0.30716315 0.13221896 0.30909702 0.13071001 0.31062141 0.12986797 0.3130677 0.12995553
		 0.31325823 0.12894613 0.31227714 0.1291135 0.30815712 0.13248676 0.31823316 0.12413335
		 0.31065232 0.115453 0.31553197 0.11162132 0.30926183 0.11339813 0.3052628 0.11634135
		 0.31098965 0.10942745 0.30745926 0.11254579 0.3045392 0.11603755 0.30223972 0.11621523
		 0.3039006 0.11350113 0.29994535 0.11372519 0.2984879 0.11670703 0.29731369 0.11320245
		 0.29731885 0.10988063 0.29309067 0.11233461 0.29496786 0.11501265 0.29153788 0.11555338
		 0.29381165 0.1178143 0.29051563 0.11828041 0.28801271 0.11603755 0.28879809 0.11334664
		 0.28685653 0.11099046 0.28914055 0.11056048 0.28835005 0.10833049 0.2860325 0.10845411
		 0.28553292 0.11164451 0.28565913 0.11377919 0.28336996 0.11531138 0.28465489 0.11712158
		 0.28233993 0.11864346 0.280146 0.11711645 0.27833575 0.12146825 0.28283176 0.12012154
		 0.28092623 0.12409222 0.27853143 0.12558317 0.28446689 0.12316775 0.27843103 0.12902337
		 0.27662081 0.12609816 0.27619332 0.1236158 0.2761032 0.11956531 0.27843875 0.11664009
		 0.27580965 0.11575687 0.27284321 0.12186742 0.27252132 0.11805373 0.26911202 0.12078846
		 0.26952919 0.11754131 0.26616105 0.12028891 0.26356283 0.11863571 0.26567951 0.11739457
		 0.26404694 0.11406249 0.26070714 0.11861771 0.26156721 0.12077296 0.26214916 0.12356174
		 0.25874239 0.11142308 0.2653293 0.10975188 0.26773182 0.11332345 0.26927939 0.11000681
		 0.26934636 0.11275434 0.27215055 0.11324877 0.27171022 0.10989612 0.27412042 0.11037248
		 0.27543887 0.11101109 0.27354106 0.11437404 0.27636331 0.11296552 0.27823019 0.11144882
		 0.27787226 0.11389256 0.28018463 0.11327195 0.2815803 0.11383587 0.28370467 0.10970294
		 0.28203094 0.10917765 0.28590119 0.10592282 0.28406259 0.10533315 0.27997088 0.10841286
		 0.27811947 0.10730821 0.28063011 0.10362589 0.27909026 0.10252374 0.27673924 0.10627306
		 0.27661824 0.10384738 0.27547747 0.10202938 0.27375221 0.10470486 0.27297196 0.10253668
		 0.27045363 0.10440099 0.26826227 0.1067726 0.26737642 0.10400957 0.26888543 0.10094273
		 0.26462889 0.10098648 0.26568723 0.098432064 0.26988196 0.097093105 0.26592928 0.094718874
		 0.26197404 0.093964398 0.2637431 0.090197146 0.26729661 0.088258147 0.26982275 0.088482201
		 0.26867425 0.084022284 0.26515165 0.083561301 0.26468813 0.08649683 0.26340574 0.084197342
		 0.26386929 0.081372559 0.26317403 0.083944976 0.26047021 0.089967966 0.26054233 0.089064121
		 0.25923938 0.087534547 0.26244271 0.077623308 0.26126334 0.076513469 0.25961277 0.076747775
		 0.26060674 0.073328137 0.26214144 0.073323011 0.26262811 0.07032311 0.26487094 0.069017589
		 0.26421174 0.06520915 0.26285985 0.065052032 0.26608896 0.059126914 0.2659061 0.061431587
		 0.26790178 0.057623088 0.26836011 0.055843771 0.26678935 0.05723685 0.26199207 0.063988566
		 0.26598081 0.056832552 0.26023075 0.065137029 0.2608462 0.068005621 0.25948659 0.07453841
		 0.26310194 0.059994698 0.26571041 0.051512599 0.26762107 0.052310824 0.27073944 0.047356486
		 0.27468696 0.045425236 0.26986906 0.050940931 0.27311105 0.047673225 0.27366206 0.048445702
		 0.27642509 0.044330835 0.27653837 0.043571174 0.27909541 0.039180756 0.27873489 0.039173067;
	setAttr ".uvst[0].uvsp[1250:1499]" 0.28050905 0.042541206 0.27921385 0.045342803
		 0.28021809 0.044565141 0.28232962 0.039731801 0.28353474 0.039850295 0.28172448 0.043942034
		 0.27983439 0.046558261 0.28138977 0.046040654 0.28522396 0.040651143 0.28555614 0.04058677
		 0.28263092 0.045345426 0.28579044 0.043725669 0.28841957 0.039348125 0.28982297 0.037885547
		 0.28820327 0.040803075 0.29306489 0.037208319 0.28607628 0.045633793 0.28890109 0.044307649
		 0.28575441 0.048154771 0.27901557 0.054221511 0.28108588 0.055532217 0.28673548 0.054981112
		 0.29206324 0.056155324 0.28875172 0.059791267 0.29324517 0.059999824 0.29101774 0.06191051
		 0.28574154 0.063367963 0.2883217 0.064995408 0.29098943 0.062440991 0.28858179 0.06512934
		 0.28737664 0.068955779 0.28918177 0.067073464 0.29240054 0.063205719 0.2946305 0.060828984
		 0.29771543 0.063239217 0.29831022 0.057654023 0.30113503 0.062438369 0.30310491 0.0591681
		 0.30142343 0.054945111 0.29862952 0.056155324 0.29949731 0.055207729 0.30253583 0.050729752
		 0.29844669 0.055910707 0.29710254 0.052037895 0.29204777 0.041562676 0.30229124 0.045788288
		 0.30406025 0.048813939 0.30727905 0.047114432 0.307055 0.045458674 0.29637122 0.041812479
		 0.29842353 0.037154198 0.31165916 0.042878509 0.31001627 0.047644913 0.31203768 0.04494369
		 0.31455863 0.04316175 0.31492171 0.046854377 0.3179422 0.046947062 0.32095242 0.044472456
		 0.32086486 0.046303332 0.31965461 0.047928154 0.31930697 0.048561573 0.3200846 0.048432827
		 0.31968293 0.048976183 0.31853959 0.050425947 0.32038334 0.050652504 0.31910613 0.053237855
		 0.31716198 0.056361318 0.31953356 0.055560529 0.31578693 0.06064105 0.31593364 0.061065912
		 0.31867865 0.058521807 0.3216683 0.054612935 0.32428706 0.058434248 0.32513937 0.056482375
		 0.32365361 0.05171597 0.32193607 0.049254298 0.32860023 0.04434371 0.32722002 0.050464571
		 0.32666898 0.053495347 0.32869038 0.052841306 0.33084565 0.050979555 0.3283942 0.058042824
		 0.32689556 0.058650553 0.33042336 0.062484741 0.33680943 0.066174746 0.34025478 0.062289059
		 0.34284526 0.067333519 0.34589925 0.065644324 0.34811375 0.06840986 0.34303838 0.071718812
		 0.34092173 0.074427724 0.34042475 0.07644397 0.34308732 0.075990736 0.33977324 0.077427626
		 0.33991492 0.080584586 0.33806604 0.081478119 0.33750466 0.081143379 0.33680168 0.082765639
		 0.33823854 0.077177823 0.3355605 0.084158719 0.33294174 0.08614409 0.3358824 0.078194976
		 0.33817673 0.074010551 0.33920678 0.070042491 0.32552567 0.064243495 0.3267411 0.062237561
		 0.32444674 0.063955069 0.32202107 0.066929221 0.32229659 0.06957382 0.32248455 0.070003808
		 0.32106826 0.072120488 0.32085714 0.07067591 0.31937906 0.074968457 0.31558087 0.07348007
		 0.31802461 0.077834487 0.31978333 0.077800989 0.32028031 0.075244009 0.32080564 0.074628592
		 0.32086745 0.075864553 0.32511365 0.075411379 0.32681832 0.069522262 0.32867491 0.07961899
		 0.32300985 0.079567432 0.32640374 0.082266092 0.33071175 0.08467114 0.32467073 0.086108029
		 0.32791784 0.088804066 0.32420206 0.089058995 0.32431024 0.091381669 0.32105026 0.092187643
		 0.31780058 0.090292454 0.31609073 0.093220234 0.3179422 0.096068203 0.31522039 0.099075854
		 0.31278184 0.099320471 0.31233379 0.097160041 0.31409767 0.093039989 0.31127548 0.093918085
		 0.31200421 0.092071772 0.31340241 0.090405703 0.31309345 0.090225518 0.31405908 0.088299394
		 0.31574056 0.085783541 0.31553715 0.085474551 0.31788814 0.081843793 0.31833619 0.081756234
		 0.31919107 0.07889539 0.31997132 0.078336596 0.32083911 0.083460867 0.31458437 0.084241152
		 0.31559893 0.082044601 0.31083515 0.076631904 0.30643699 0.079776049 0.30618981 0.077074826
		 0.30984631 0.074262917 0.30560783 0.074610531 0.30700094 0.071744561 0.31484702 0.070317984
		 0.31053901 0.068033934 0.31241104 0.066501796 0.31262478 0.06497997 0.31351319 0.064902663
		 0.31391487 0.062994599 0.31348741 0.063038349 0.31386596 0.061941445 0.31171581 0.063226342
		 0.31421357 0.060198128 0.31356466 0.058084011 0.31115186 0.058547556 0.31381187 0.054072142
		 0.30982316 0.057919204 0.31359556 0.051793218 0.3118265 0.053670406 0.31315008 0.051674783
		 0.31443503 0.050147831 0.31344107 0.049612164 0.31112611 0.053443849 0.3031899 0.051520288
		 0.30890903 0.057484031 0.30967125 0.057373345 0.30860257 0.060344934 0.30718634 0.061024725
		 0.30583704 0.062688172 0.30792022 0.061256468 0.30537349 0.064864039 0.30874678 0.062222123
		 0.30928239 0.059827328 0.3069005 0.067869127 0.31179306 0.064488113 0.30296332 0.069687068
		 0.29935053 0.068314612 0.30080542 0.071955681 0.30148521 0.07584399 0.29961577 0.076310039
		 0.2981171 0.072537661 0.29531807 0.073547065 0.29632747 0.077785552 0.2929078 0.077600121
		 0.28919464 0.073462069 0.28753373 0.078164101 0.28527802 0.072305858 0.28363517 0.072504163
		 0.28579563 0.0686571 0.28285751 0.072228611 0.28542736 0.068626165 0.2820541 0.0725016
		 0.28005075 0.069043338 0.27875033 0.073405385 0.27775639 0.071839809 0.27691436 0.067160964
		 0.27890998 0.063040972 0.27646372 0.064101875 0.27782077 0.059721768 0.27433673 0.065093279
		 0.27251104 0.063962817 0.27626801 0.057635963 0.27480283 0.057674587 0.27714095 0.05453819
		 0.27679333 0.054502189 0.27406639 0.057952702 0.27320117 0.059350967 0.27160725 0.062708795
		 0.27054113 0.061117411 0.27189049 0.05881536 0.27397111 0.056217134 0.27385005 0.055447221
		 0.27189305 0.056961298 0.27420542 0.05250138 0.27896664 0.049303234 0.27914172 0.049377859
		 0.26957551 0.053685904 0.27129048 0.050611317 0.26821336 0.055385411 0.26926392 0.058328688
		 0.2690708 0.060386121 0.26871032 0.061284781 0.26817727 0.061068475 0.26736102 0.062755108
		 0.26599109 0.066308677 0.26672497 0.065435708 0.26856869 0.064140499 0.26834983 0.062639236
		 0.26875925 0.06413275 0.26814124 0.065203965 0.26722196 0.066687226 0.26847342 0.066828847
		 0.26869744 0.066061437 0.26980469 0.064686418 0.26839873 0.071615815 0.26692325 0.073781371;
	setAttr ".uvst[0].uvsp[1500:1749]" 0.2657851 0.069269955 0.26371735 0.073444068
		 0.26772666 0.077679932 0.26926136 0.075864553 0.27288702 0.077579558 0.27208617 0.075395942
		 0.27413332 0.071644068 0.27308786 0.070163488 0.27077806 0.071031272 0.27529466 0.076843083
		 0.27019355 0.083041191 0.27500367 0.079902232 0.27904904 0.076168418 0.28043443 0.074880898
		 0.28259486 0.076168418 0.2811915 0.074924707 0.28253049 0.072419226 0.28213906 0.07498908
		 0.27966961 0.079971731 0.2776199 0.082042038 0.27932972 0.084712327 0.27292049 0.084931195
		 0.27719244 0.088186085 0.2813099 0.08734405 0.27936578 0.090699315 0.28252274 0.090905309
		 0.28015885 0.094775558 0.27638903 0.091778219 0.27713582 0.09550941 0.27799329 0.098697305
		 0.28196138 0.098156571 0.28424543 0.094518065 0.2840935 0.098699868 0.28509778 0.10015476
		 0.28246608 0.10432887 0.28700846 0.10016507 0.28858694 0.10155559 0.29097143 0.098074138
		 0.28979462 0.097103357 0.28887019 0.095542908 0.28693891 0.097329974 0.28862554 0.095166922
		 0.28832686 0.094664812 0.28578013 0.094963551 0.28854316 0.090843499 0.28970963 0.092393637
		 0.28919721 0.09390521 0.2903946 0.092839122 0.29177997 0.090202332 0.29377303 0.088580012
		 0.29243401 0.092988491 0.29556525 0.088549137 0.29509401 0.091816843 0.29739094 0.088008404
		 0.29886127 0.089826345 0.29932222 0.084488332 0.30112728 0.087833285 0.3007153 0.092473447
		 0.30385685 0.09262538 0.30541727 0.088003218 0.30963776 0.091160178 0.31223854 0.087341428
		 0.31100509 0.090977371 0.31275612 0.088788629 0.30930555 0.08468914 0.30350921 0.083486617
		 0.30177104 0.080821514 0.30149552 0.077497125 0.29903638 0.080267847 0.29828188 0.079294503
		 0.29605964 0.083605111 0.29683474 0.084166467 0.29522535 0.083370745 0.29376531 0.08142662
		 0.29145038 0.086350083 0.29116195 0.084557891 0.28866935 0.084282339 0.28962725 0.081527054
		 0.285157 0.084058285 0.28542483 0.087506294 0.28840667 0.088255584 0.28632349 0.091309607
		 0.29224086 0.087735415 0.28360167 0.081609428 0.29210183 0.088698506 0.30731252 0.095035613
		 0.30627733 0.09753859 0.30288088 0.097327411 0.30297616 0.10211694 0.30915105 0.1015504
		 0.30942404 0.098653555 0.30309203 0.1069271 0.30908155 0.1086781 0.30554864 0.10892528
		 0.29625535 0.10678542 0.29237223 0.10804981 0.29356706 0.10390913 0.29008818 0.10480785
		 0.29276106 0.10127491 0.29748878 0.10269892 0.29707938 0.09995389 0.30054793 0.10053849
		 0.29936853 0.096959174 0.29724416 0.093838215 0.29532835 0.097646713 0.29305977 0.094955802
		 0.31493714 0.10334778 0.31603155 0.10143971 0.31905463 0.10259074 0.31322992 0.10756826
		 0.31727266 0.10739833 0.32392138 0.10207057 0.32088545 0.1049211 0.3188512 0.10793394
		 0.32152662 0.10622925 0.32456776 0.10267317 0.32425103 0.10489023 0.3221781 0.10742152
		 0.32918733 0.1033169 0.3272638 0.10572195 0.33065766 0.10370058 0.3341597 0.09872818
		 0.33443522 0.097958267 0.33779564 0.094237387 0.33760768 0.094912052 0.34307963 0.089527667
		 0.34230196 0.089365423 0.34431815 0.087604105 0.34444433 0.086290836 0.3436873 0.08651489
		 0.34732839 0.082278967 0.34694213 0.08016485 0.34813181 0.081905603 0.35346726 0.079057574
		 0.35455906 0.081107318 0.35071969 0.074167609 0.34809056 0.084519207 0.34799531 0.083180189
		 0.34703743 0.083576739 0.3456057 0.078954577 0.3449671 0.077574372 0.34318775 0.076186419
		 0.34607691 0.073248327 0.33987111 0.081962228 0.34153977 0.081251502 0.34299204 0.080909014
		 0.34148568 0.082992196 0.34375682 0.081547618 0.34103763 0.089622915 0.33801451 0.084496021
		 0.33695361 0.085595608 0.33596995 0.084872007 0.33456141 0.086795568 0.33302671 0.090856373
		 0.33024824 0.092671752 0.32994953 0.092617691 0.32758307 0.095339477 0.32613337 0.094765246
		 0.32514712 0.099140227 0.32798222 0.09633857 0.32755476 0.098195195 0.32966629 0.09558928
		 0.32982594 0.095625281 0.33156151 0.093696594 0.33154091 0.093029678 0.33223099 0.09268719
		 0.33403611 0.090825438 0.33319148 0.093418539 0.33640772 0.087053061 0.33681971 0.089872718
		 0.33307821 0.095872521 0.33107743 0.096601248 0.32937017 0.097778022 0.32980531 0.098099887
		 0.3301298 0.098532498 0.32875732 0.099408031 0.33160785 0.099686146 0.33445585 0.096856177
		 0.3284792 0.10213494 0.3268415 0.10081398 0.32583207 0.10020113 0.32049665 0.10072899
		 0.32423297 0.09370172 0.33062676 0.089491606 0.32013357 0.098480999 0.31977049 0.096518874
		 0.33326364 0.087822974 0.33980161 0.09573859 0.33400264 0.10183114 0.33578196 0.098645806
		 0.33025599 0.10544646 0.32394201 0.10836649 0.32143393 0.10875535 0.31928894 0.10930127
		 0.27362087 0.098663867 0.27289471 0.09497124 0.27004418 0.063231468 0.28117859 0.049050868
		 0.28122237 0.049516916 0.28670457 0.043478489 0.28164467 0.061323404 0.28489175 0.058120072
		 0.29658753 0.068548918 0.30827811 0.049367607 0.31742719 0.049030244 0.31567362 0.05128336
		 0.31605214 0.062005818 0.31715426 0.06730777 0.33609095 0.048978746 0.33208424 0.045134246
		 0.33146363 0.043787479 0.32992893 0.043511987 0.32277292 0.044657826 0.3241815 0.042072535
		 0.3220571 0.044323087 0.29577124 0.058601618 0.29428032 0.059899449 0.27555472 0.042559206
		 0.27683195 0.039865732 0.27339688 0.042654514 0.26830345 0.038058102 0.26557907 0.039137006
		 0.26298347 0.10291523 0.26430699 0.10572457 0.26095438 0.10644817 0.25380352 0.1069271
		 0.27185699 0.10715628 0.27385265 0.1062215 0.27032229 0.12911868 0.27341744 0.1295976
		 0.27141926 0.14037406 0.26848114 0.13792783 0.2692408 0.14101267 0.26802281 0.13995177
		 0.28712431 0.1203301 0.28818265 0.12581748 0.29177997 0.12140131 0.29698926 0.1205284
		 0.30728418 0.14451218 0.30292982 0.14661592 0.2988793 0.1452924 0.30059171 0.14823818
		 0.29792655 0.14952314 0.29794461 0.15277028 0.29377046 0.15449297 0.29232585 0.14837468
		 0.2882908 0.15089047 0.2889809 0.14163584 0.2959747 0.14644343 0.29054654 0.14075518;
	setAttr ".uvst[0].uvsp[1750:1999]" 0.28949076 0.13923335 0.29532319 0.14380401
		 0.29526398 0.14132428 0.29630169 0.15685165 0.29906985 0.15791517 0.30068436 0.16253221
		 0.30500272 0.16038203 0.30452377 0.16295707 0.30874938 0.16136569 0.32247683 0.14734209
		 0.31945893 0.15235054 0.32218069 0.15308702 0.31472859 0.15135914 0.32481238 0.15922582
		 0.31653881 0.1788398 0.32024941 0.17850763 0.32154211 0.18092042 0.32754964 0.18424219
		 0.32544839 0.18377095 0.32780713 0.18469024 0.32402956 0.18398982 0.32880878 0.18576407
		 0.32699084 0.188182 0.33105165 0.19013906 0.32623124 0.193932 0.3293058 0.1957165
		 0.32124853 0.19458354 0.32213435 0.19900227 0.31842116 0.19708639 0.31855506 0.19364619
		 0.32259014 0.18690223 0.31655684 0.19195962 0.31865808 0.18570739 0.31805292 0.18178821
		 0.31317326 0.18624043 0.31133729 0.18336409 0.31174409 0.18750471 0.31427023 0.18888235
		 0.31149179 0.19261879 0.31443247 0.19437754 0.31170037 0.19755763 0.31603926 0.20049834
		 0.309921 0.19981593 0.30832189 0.20477545 0.31253207 0.20491964 0.31672937 0.20545012
		 0.3205198 0.20327938 0.32798481 0.20298576 0.33128086 0.19833535 0.33351338 0.20180386
		 0.33264557 0.20563811 0.32670242 0.20649296 0.33121905 0.20875639 0.3365545 0.20711875
		 0.3357614 0.21187741 0.3388823 0.21083707 0.33652616 0.21687549 0.33000621 0.21357429
		 0.32700372 0.21546435 0.33929175 0.21911317 0.32735136 0.21715099 0.32280642 0.21488243
		 0.32440034 0.21677762 0.32693678 0.21796215 0.33616823 0.21986771 0.33227995 0.21956897
		 0.33548585 0.22095948 0.33342326 0.2203595 0.32926717 0.21915442 0.33285674 0.22193027
		 0.33087915 0.22409582 0.32633421 0.21947622 0.327117 0.21887887 0.32389826 0.21722311
		 0.32691872 0.21830201 0.32131293 0.21568841 0.32004085 0.21568066 0.32068205 0.21517086
		 0.318501 0.21459657 0.31822801 0.21483862 0.31604442 0.2137211 0.31582296 0.21314174
		 0.31511998 0.21282238 0.31494489 0.21191597 0.31807351 0.2131958 0.31620923 0.21135724
		 0.31260416 0.21172029 0.30992618 0.20816159 0.30835536 0.20990747 0.31181109 0.21259063
		 0.31324536 0.21246707 0.31437838 0.21302581 0.31350803 0.21299231 0.31440926 0.21348423
		 0.31237245 0.21300006 0.31421101 0.21385241 0.31373718 0.21452701 0.31317326 0.21660769
		 0.3171182 0.21589696 0.31653881 0.21893036 0.30875966 0.21595103 0.31830016 0.22055775
		 0.32902509 0.22580826 0.3193765 0.22262037 0.32928517 0.22774208 0.33523861 0.22871292
		 0.33568928 0.22851974 0.34187704 0.23329902 0.33778277 0.23230505 0.33294433 0.22912484
		 0.33497083 0.23085529 0.33274084 0.23024243 0.33444813 0.2316947 0.3288835 0.22863305
		 0.32885519 0.22814119 0.32378235 0.2254014 0.31912413 0.22318685 0.31958765 0.22423488
		 0.31210977 0.222574 0.3109948 0.21996033 0.31638172 0.2216779 0.31029695 0.21879393
		 0.30332381 0.21545923 0.30612025 0.21942735 0.30177104 0.21673644 0.29676777 0.22208989
		 0.30295816 0.22631556 0.29632747 0.2277987 0.3066121 0.23249304 0.30224228 0.23671347
		 0.29648197 0.23152739 0.29593605 0.23158658 0.29523566 0.23083985 0.29037914 0.22944158
		 0.2923027 0.22858155 0.28809768 0.22758245 0.28574926 0.22466755 0.29174137 0.23139346
		 0.3009007 0.2391237 0.30972272 0.24228841 0.31194499 0.24283433 0.30976391 0.24464196
		 0.3154676 0.24408835 0.31625298 0.24365312 0.31624269 0.2441141 0.32198501 0.24215966
		 0.32091123 0.24533987 0.3219927 0.24591148 0.32108375 0.24666333 0.32125884 0.24945724
		 0.32339868 0.24547112 0.32271373 0.24332613 0.32346308 0.24366087 0.32408106 0.24163437
		 0.321264 0.24168324 0.32455742 0.24080777 0.32463214 0.24152362 0.3262544 0.2401073
		 0.32560548 0.23967218 0.32451111 0.23914945 0.32625955 0.23834085 0.32671273 0.23863959
		 0.32698056 0.2377435 0.32541749 0.23699158 0.32597375 0.23633754 0.32466561 0.23768431
		 0.32894015 0.23096859 0.31959793 0.2352792 0.3249025 0.22863817 0.31977305 0.22809231
		 0.31289515 0.22878504 0.31304452 0.23440623 0.31884605 0.24142063 0.32694191 0.23630142
		 0.33443007 0.23568088 0.33027914 0.2380628 0.33657509 0.23717183 0.33553991 0.23862416
		 0.32990834 0.23999661 0.33225417 0.24066609 0.33100274 0.241364 0.3295221 0.24064302
		 0.3268286 0.2409597 0.32650673 0.24481964 0.32474801 0.24511576 0.32367939 0.24897832
		 0.32458833 0.24878258 0.32687241 0.24855602 0.32504153 0.25270438 0.32513425 0.25373697
		 0.32317722 0.25769478 0.3218382 0.25915217 0.32300472 0.25267857 0.31884086 0.2589308
		 0.32188201 0.25308037 0.32261589 0.25068551 0.32026231 0.25120568 0.32217041 0.25038946
		 0.31930953 0.25340474 0.3200537 0.26054275 0.32175842 0.26004839 0.32051468 0.2616809
		 0.31974989 0.26204395 0.3181302 0.2606715 0.31922716 0.26225257 0.31791645 0.26204658
		 0.31716713 0.264328 0.32850239 0.24516213 0.32966629 0.24239141 0.33755875 0.23963094
		 0.3417818 0.23672897 0.33984795 0.23668516 0.35205871 0.23143464 0.34480485 0.23660535
		 0.34917983 0.2349419 0.35518733 0.23148614 0.35310674 0.23026562 0.34479973 0.22497904
		 0.34300232 0.2239877 0.34259552 0.22459286 0.33959559 0.22534472 0.34116119 0.22439456
		 0.33802223 0.22386158 0.33766174 0.222368 0.33805314 0.22197402 0.33520517 0.22155941
		 0.33885658 0.2219792 0.34121785 0.22375339 0.34168908 0.22133547 0.34364608 0.22100329
		 0.34687519 0.22491467 0.34781766 0.22329247 0.34996778 0.22194827 0.35255826 0.22591639
		 0.34509584 0.21899474 0.34018782 0.21743166 0.34608725 0.20636421 0.3418977 0.20488107
		 0.34571898 0.19954038 0.34194145 0.20007348 0.33883339 0.19876021 0.33636394 0.20427334
		 0.33551675 0.19880402 0.335594 0.19614655 0.33468759 0.22232676 0.33664203 0.22342634
		 0.33733985 0.22439969 0.32640889 0.22225469 0.34629837 0.22905022 0.34725371 0.23285609;
	setAttr ".uvst[0].uvsp[2000:2249]" 0.34232256 0.23538476 0.33973977 0.23379594
		 0.34007454 0.23528433 0.3388488 0.23459935 0.33863771 0.2336337 0.33771583 0.23438305
		 0.33608839 0.23226643 0.33849862 0.23600793 0.30291438 0.21423608 0.30987468 0.21812952
		 0.30478901 0.21366441 0.30369976 0.20928687 0.30735114 0.20685089 0.30396238 0.20448709
		 0.3063263 0.2033515 0.30073592 0.20176524 0.29592833 0.19833016 0.29884583 0.19818854
		 0.30262339 0.1940273 0.3070035 0.19577831 0.30305344 0.19847953 0.30213928 0.20035672
		 0.30820602 0.19170713 0.30107322 0.18786269 0.29945868 0.19100934 0.29860377 0.18707216
		 0.29857287 0.18408769 0.30363795 0.18568677 0.30201054 0.18158478 0.30805412 0.18309891
		 0.31372947 0.17990839 0.29920891 0.17910242 0.29528716 0.18271005 0.29638669 0.18423188
		 0.28891912 0.1900695 0.29534635 0.19018537 0.29841578 0.19380844 0.32137731 0.21734929
		 0.31697142 0.21452701 0.32006919 0.21158123 0.32412484 0.21109194 0.31887436 0.20968086
		 0.3210451 0.20739424 0.32703719 0.21021134 0.26462632 0.17694455 0.28435874 0.22279286
		 0.28393129 0.2232461 0.26190966 0.17643213 0.2624504 0.17104006 0.30071273 0.12357205
		 0.2814799 0.13779908 0.28106532 0.13621545 0.24917361 0.10840261 0.25485927 0.097304225
		 0.23757569 0.087400675 0.24206911 0.085075438 0.24239615 0.077679932 0.24974009 0.074839711
		 0.24822858 0.072694719 0.24191204 0.073928177 0.23908982 0.075197637 0.23748298 0.077509999
		 0.24030265 0.072388291 0.24116786 0.069936872 0.24114984 0.066051126 0.2417601 0.060841918
		 0.24563295 0.061063349 0.25342497 0.035215259 0.25186193 0.036623776 0.29214561 0.027608633
		 0.32837364 0.032163799 0.33323273 0.027279019 0.33324814 0.026792347 0.35910654 0.092084646
		 0.36040953 0.095524907 0.36918005 0.10201651 0.36889678 0.10112041 0.37189671 0.099552214
		 0.37193534 0.099943638 0.37499189 0.098426938 0.37540132 0.099083543 0.37691543 0.098426938
		 0.3767069 0.097996891 0.37776777 0.096621811 0.38003379 0.10152209 0.38421562 0.096263885
		 0.38216332 0.098898172 0.38311869 0.098774552 0.38526109 0.096384943 0.38565767 0.096511126
		 0.38799575 0.093488038 0.38784382 0.095921457 0.38889185 0.09334898 0.38906953 0.093441725
		 0.38962576 0.098323941 0.39137158 0.094067395 0.39122227 0.096014142 0.39279559 0.093106925
		 0.39250466 0.097239852 0.39382049 0.09185034 0.39478093 0.094914615 0.39392859 0.098452687
		 0.39596289 0.096135139 0.39680752 0.096693933 0.39312521 0.099750519 0.39214668 0.10043287
		 0.39200506 0.10161483 0.3931587 0.10100967 0.39279047 0.10193157 0.3913433 0.10289204
		 0.3905682 0.10265255 0.38742414 0.10646105 0.38867298 0.10680866 0.38637352 0.10808331
		 0.3866542 0.1044808 0.38558814 0.10726184 0.3856293 0.1077897 0.38476151 0.10919565
		 0.38378814 0.10697347 0.38275817 0.10898966 0.38131613 0.10425162 0.38410231 0.10391945
		 0.38522759 0.10126203 0.38482332 0.10016769 0.38475639 0.09966296 0.38073674 0.10186976
		 0.37790683 0.10435724 0.37849137 0.10620093 0.37677637 0.10539752 0.37663731 0.1051864
		 0.37398764 0.10704553 0.37585708 0.10814762 0.37389234 0.10934246 0.37492749 0.10924464
		 0.37557122 0.11025143 0.37236536 0.1110729 0.37367606 0.11149776 0.37301427 0.11441785
		 0.37512317 0.11301959 0.37462625 0.11523926 0.37598071 0.1152727 0.37833172 0.11404705
		 0.37413442 0.11858165 0.37926644 0.1163491 0.3837212 0.11182994 0.38267058 0.11360925
		 0.38540784 0.11062998 0.37742528 0.1134882 0.37753606 0.11148745 0.37508455 0.12095326
		 0.37393096 0.12507844 0.37365547 0.12894869 0.38612369 0.10294092 0.38941973 0.10064149
		 0.38481304 0.10601294 0.39376381 0.10158134 0.39623585 0.098457813 0.39802805 0.093760967
		 0.39563847 0.092903495 0.38742414 0.093135297 0.38225862 0.092190206 0.38459411 0.089174867
		 0.37423739 0.13138211 0.37516439 0.13385153 0.37907848 0.14057237 0.38269377 0.15032911
		 0.38436753 0.15430236 0.38590744 0.16147643 0.38571173 0.16927099 0.38759664 0.17049158
		 0.38608253 0.18050843 0.38454264 0.17038858 0.38378814 0.16766167 0.38076764 0.16830796
		 0.38004151 0.16368067 0.37519789 0.16190386 0.37579533 0.16457671 0.36642218 0.1588499
		 0.37014568 0.16315019 0.36575526 0.16085327 0.36286867 0.1588499 0.35993573 0.16518956
		 0.35862502 0.16231072 0.35556072 0.16646165 0.35324836 0.16173649 0.35603711 0.15721476
		 0.35156173 0.1579203 0.35028452 0.15536582 0.34851032 0.16051853 0.34553102 0.15622342
		 0.3457782 0.15311015 0.34799272 0.15239429 0.35537273 0.15378737 0.33805832 0.15273941
		 0.3411921 0.15494096 0.3419517 0.15893227 0.34665114 0.16393304 0.35179603 0.16496301
		 0.34938586 0.16835177 0.34515506 0.1694178 0.34840989 0.17183572 0.35055491 0.1740734
		 0.35321745 0.16841352 0.3536604 0.1752013 0.35216171 0.17852306 0.34791806 0.17714542
		 0.34627005 0.17377216 0.35577703 0.17814195 0.3571547 0.18062687 0.35728341 0.18340015
		 0.36061037 0.18299848 0.3586688 0.17930591 0.36247984 0.18019938 0.36136487 0.17348373
		 0.35740447 0.17170185 0.3644729 0.17603564 0.36662045 0.17318505 0.36703765 0.17680299
		 0.36663076 0.18154615 0.37032592 0.17761922 0.36851054 0.18528765 0.37629229 0.17814708
		 0.3754811 0.17253351 0.37050623 0.17375928 0.37877715 0.18561727 0.38436499 0.1842705
		 0.38062862 0.19155264 0.38472807 0.19521439 0.38665932 0.1866653 0.38660523 0.19256473
		 0.38780519 0.19368219 0.38895884 0.20027685 0.38646364 0.19877052 0.38774857 0.20140731
		 0.38743439 0.20396429 0.38604644 0.20492995 0.38564992 0.20189142 0.386152 0.20123482
		 0.38509113 0.20112926 0.38542849 0.20039022 0.38431865 0.19699883 0.38401732 0.19744438
		 0.38034022 0.1928634 0.37900895 0.19323421 0.3797428 0.19442385 0.37851453 0.19463241
		 0.38402766 0.1984486 0.38288179 0.19932413 0.38447571 0.20402354 0.38551345 0.20473164;
	setAttr ".uvst[0].uvsp[2250:2471]" 0.38450921 0.20500982 0.38363108 0.20413685
		 0.38277361 0.2048192 0.38494954 0.20607066 0.38251352 0.2068792 0.38096339 0.2072655
		 0.38274011 0.20735818 0.38174877 0.20769554 0.3832629 0.20932037 0.38086036 0.20933324
		 0.37848362 0.20865601 0.37882352 0.20794016 0.37314302 0.20788091 0.37718838 0.2097916
		 0.37232673 0.2087307 0.36883759 0.21658713 0.37641591 0.21254432 0.38280192 0.21096581
		 0.38495466 0.21266013 0.38650739 0.2116971 0.38581213 0.20738649 0.38510397 0.20646465
		 0.38751167 0.20599341 0.39149779 0.20910662 0.39802551 0.21177179 0.396429 0.2151348
		 0.39524445 0.20775992 0.39134842 0.20393854 0.39417842 0.20459265 0.3913562 0.20280039
		 0.39364281 0.20408273 0.3915441 0.20200729 0.39380759 0.20303214 0.3941063 0.20305532
		 0.38967985 0.19340414 0.38858286 0.18933302 0.38680866 0.18575376 0.38847989 0.18661892
		 0.38771507 0.17999339 0.39647275 0.20366818 0.3961328 0.20428622 0.39803323 0.20327419
		 0.39789417 0.20379436 0.39969409 0.20402354 0.39923832 0.20451283 0.39679205 0.20436859
		 0.40163568 0.20699251 0.4002271 0.20831615 0.40251631 0.2060166 0.4010357 0.20285451
		 0.40342534 0.20348275 0.36690119 0.21102762 0.36002585 0.20358062 0.36690632 0.20684063
		 0.36357936 0.20112151 0.36743423 0.20323557 0.36312103 0.19990611 0.36047131 0.1984306
		 0.3627708 0.19899964 0.35751003 0.19662297 0.36304632 0.19421273 0.3573581 0.19191319
		 0.36314934 0.19396549 0.36863676 0.19672847 0.36886334 0.19647872 0.37495068 0.19965112
		 0.36867532 0.20253003 0.37333617 0.20515144 0.36830714 0.20288533 0.37260485 0.20640546
		 0.37356788 0.20631534 0.37826991 0.20755386 0.37899089 0.20597798 0.3750537 0.19932669
		 0.37353444 0.1923973 0.38054365 0.2018348 0.36681873 0.1903013 0.37353444 0.19148058
		 0.37376359 0.1911999 0.37552494 0.18841374 0.36900243 0.18963689 0.36472267 0.18804294
		 0.36590719 0.18940771 0.36146528 0.18782151 0.36152965 0.18738627 0.3610687 0.18674511
		 0.35897264 0.18592113 0.35858896 0.18682241 0.35721391 0.18544471 0.35710061 0.18570739
		 0.35682765 0.18599325 0.35608348 0.18550909 0.35615042 0.18603182 0.35502511 0.18517697
		 0.35562769 0.18491429 0.35472903 0.18495291 0.354711 0.18554777 0.35363463 0.18539834
		 0.35246298 0.18659836 0.35242179 0.18543959 0.34804165 0.18548852 0.3534286 0.184425
		 0.35617617 0.18382245 0.35394102 0.18470573 0.34945276 0.18838799 0.34511128 0.18623781
		 0.3430281 0.18389457 0.33763084 0.18365252 0.34476623 0.18699491 0.34159124 0.18720865
		 0.34608725 0.18947977 0.34781766 0.19041705 0.34890947 0.19305915 0.34424865 0.19046348
		 0.3396883 0.1882695 0.34978235 0.19164801 0.35017893 0.19341183 0.34938067 0.19371319
		 0.35069138 0.19438261 0.35108534 0.19440329 0.35127333 0.19503152 0.35070166 0.19485646
		 0.35131708 0.195647 0.35252735 0.19558001 0.35302436 0.19649673 0.35192996 0.19710189
		 0.35414189 0.19740057 0.35412899 0.1965276 0.3561298 0.19739282 0.35553756 0.19635254
		 0.35721132 0.1971817 0.35451525 0.19554913 0.35712379 0.19589418 0.35454103 0.1949234
		 0.35365522 0.19539976 0.35224667 0.19452429 0.35248873 0.19518089 0.35316852 0.18984026
		 0.35737357 0.1915012 0.3611846 0.18833649 0.35847309 0.18738115 0.36527377 0.18981194
		 0.36796206 0.19002569 0.35952628 0.19909239 0.35670146 0.19996792 0.35034889 0.1956985
		 0.36347637 0.18543446 0.37249157 0.15644997 0.34907681 0.14714384 0.34576535 0.14605463
		 0.34822193 0.14817643 0.36178714 0.22727859 0.38190836 0.21903849 0.38214016 0.22151566
		 0.38069817 0.22164702 0.38044834 0.21758878 0.38036081 0.22027451 0.3798947 0.22181952
		 0.38385767 0.22286755 0.38268864 0.22546834 0.38815027 0.22822624 0.38925496 0.22902191
		 0.39125058 0.23018324 0.39290634 0.23107678 0.39345226 0.22737384 0.39370975 0.22764677
		 0.39405221 0.22828543 0.39378953 0.22491986 0.39445651 0.22985107 0.39622551 0.22875154
		 0.3962487 0.23366463 0.39755422 0.23277628 0.39830616 0.23266554 0.39510795 0.22442031
		 0.39901686 0.23192132 0.3993001 0.22664255 0.40002111 0.23171538 0.39957818 0.22732753
		 0.4015249 0.23087329 0.40110776 0.22822624 0.40050265 0.22582626 0.40137818 0.22678673
		 0.39928213 0.22532159 0.40218675 0.22874123 0.39391574 0.22133547 0.39554828 0.21955097
		 0.39274409 0.22185558 0.40601063 0.2182222 0.40574023 0.20341325 0.40533599 0.20175493
		 0.40688869 0.20207167 0.40725434 0.20086652 0.41031089 0.20152837 0.41064051 0.20154119
		 0.41216496 0.20088458 0.4132593 0.20046747 0.41487643 0.20387417 0.41972262 0.19860053
		 0.41935185 0.20274889 0.41603777 0.20671189 0.41903254 0.20541662 0.42092258 0.2034055
		 0.42045134 0.20543468 0.41952434 0.20947486 0.42114404 0.19987518 0.42150968 0.20273864
		 0.42086595 0.22150278 0.42216632 0.22018182 0.42849061 0.22366065 0.4197458 0.22539109
		 0.41778105 0.22627687 0.4170472 0.22855842 0.42316285 0.23262691 0.42667261 0.22821844
		 0.43169135 0.23164582 0.40115413 0.22043931 0.40040481 0.22393876 0.40061855 0.22464174
		 0.40660802 0.2253499 0.41422492 0.22863817 0.40834099 0.22667342 0.40344849 0.23100978;
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr -s 2472 ".vt";
	setAttr ".vt[0:165]"  2.032464743 160.32530212 16.033859253 1.39139664 159.96975708 16.24633789
		 1.56417346 158.64129639 16.45698547 1.40291953 158.19902039 16.56587219 1.56980836 156.39875793 16.84851074
		 1.76771808 158.99867249 16.27900696 1.69502389 158.065231323 16.37670898 1.71465945 158.89006042 15.90524292
		 1.83625603 159.46099854 16.047973633 1.87841332 159.61187744 16.17425537 1.9494468 159.74838257 16.10250854
		 2.090656519 160.26747131 15.92675781 1.9377197 160.30554199 15.65324402 2.1797049 160.66670227 15.47406006
		 2.48709321 161.05418396 15.30673218 2.60975099 160.96826172 15.66091919 3.093956947 161.46942139 14.9262085
		 3.15207767 161.42671204 15.34524536 2.9011848 162.22885132 15.31030273 3.93489766 162.53692627 14.74478149
		 2.49338078 162.35420227 15.38760376 2.61664248 161.81115723 15.47904968 2.30653667 161.89933777 15.28182983
		 2.10658431 161.86842346 15.29797363 2.26019192 161.5604248 15.58659363 2.051714182 161.5892334 15.66394043
		 1.88334215 161.90293884 15.69465637 1.40326571 160.7640686 16.063812256 1.70445085 160.84289551 15.89581299
		 1.1738559 160.10267639 16.14750671 0.93708801 160.11048889 16.22639465 1.14102793 156.050643921 16.86273193
		 0.69654149 155.68582153 16.99902344 0.78780997 155.44987488 16.51502991 0.3878611 155.35649109 16.80451965
		 0.41480109 155.43516541 16.84283447 -0.27974764 155.29612732 16.6945343 -0.26949027 155.081817627 16.55041504
		 -0.55140394 155.66847229 16.95677185 -0.29074222 155.58688354 16.83175659 -0.29721636 156.58657837 16.54837036
		 0.25291654 157.095504761 16.40945435 0.39753228 156.37051392 16.65263367 0.36228412 160.57435608 15.96891785
		 -0.10813883 159.43432617 15.93128967 -0.097144254 158.4552002 16.11709595 -0.2020227 159.35568237 15.95710754
		 -0.46749777 160.78416443 15.96990967 -0.37689534 159.8120575 16.038925171 -0.37154016 157.41593933 16.48118591
		 -0.4926528 159.1413269 16.39115906 -0.62325007 160.66372681 16.16278076 -0.90997249 155.83711243 16.9664917
		 -0.9195506 160.0859375 16.22822571 -1.14436495 160.037963867 16.16299438 -1.14597237 156.24713135 16.84030151
		 -1.12370777 156.040313721 16.83093262 -1.55146277 156.39176941 16.84114075 -1.39896977 158.22377014 16.56355286
		 -1.37835729 159.94482422 16.24992371 -1.51905215 158.79336548 16.43734741 -1.78123701 159.55505371 16.23471069
		 -1.72410214 158.83470154 16.32952881 -1.80387437 159.32521057 16.19380188 -1.6322962 157.40490723 16.53843689
		 -1.72813404 159.079742432 15.93756104 -1.47395074 156.19644165 16.42037964 -1.67107451 159.017196655 15.80210876
		 -1.372949 158.097518921 15.90097046 -1.48733866 160.061950684 15.5660553 0.036086157 159.84020996 15.65621948
		 -1.48990083 161.00024414063 15.37225342 -1.82398057 160.71539307 15.43589783 -1.92145216 160.30929565 15.66290283
		 -2.41348219 161.076385498 15.2052002 -2.071316481 160.27693176 15.92887878 -1.86684382 159.84521484 15.87277222
		 -2.03079772 160.39241028 16.011383057 -2.61009097 160.98223877 15.65687561 -2.55772495 161.78541565 15.48381042
		 -2.14162183 161.51757813 15.62236023 -1.59318066 160.69856262 15.93920898 -1.39655876 160.8041687 16.053878784
		 -1.8509295 161.86528015 15.70358276 -1.39976478 161.47499084 15.89811707 -1.19543862 160.96713257 16.0039672852
		 -1.15745544 161.33506775 15.64505005 -0.73096156 161.97216797 15.52578735 -0.41067812 161.47702026 15.7293396
		 -0.020840134 161.36659241 15.99697876 0.040997177 161.52688599 16.056762695 -0.30192778 161.64041138 15.87658691
		 -0.028473236 161.76605225 16.43896484 0.092115365 161.74942017 16.36286926 0.39782074 161.63829041 15.75999451
		 0.18641666 161.41584778 15.9568634 0.47392514 161.55451965 15.70542908 0.71408099 161.77661133 15.60852051
		 0.73928934 160.97271729 15.93002319 1.18028104 161.28268433 15.67456055 0.74565238 162.055023193 15.50468445
		 1.15180457 162.080535889 15.53355408 1.42825198 161.48158264 15.89671326 1.21694112 160.95539856 16.022903442
		 0.676 160.67797852 16.16212463 1.38910079 162.076416016 15.76121521 1.50335729 162.88749695 15.30276489
		 1.86201036 162.91429138 15.5453949 1.55897367 163.19255066 15.054840088 1.21712327 163.40957642 15.080917358
		 1.18544078 163.53593445 15.034057617 1.048649073 163.32580566 15.188797 0.56431884 163.26806641 15.8361969
		 0.97556859 163.85566711 15.31221008 0.97896993 163.97447205 15.21052551 0.77811629 164.16912842 14.82641602
		 1.20244765 163.40718079 14.94406128 1.51492906 163.22824097 14.99058533 1.32667732 163.05015564 14.92225647
		 2.099684 163.10891724 14.68478394 2.24334955 163.43162537 14.76792908 2.65107346 163.20251465 14.50918579
		 1.94566345 161.47499084 14.97671509 2.99394965 161.67617798 14.75439453 1.70361602 160.67256165 15.46557617
		 1.29442215 161.097198486 15.39196777 0.036086157 159.84020996 15.65621948 0.86578369 161.22529602 15.4654541
		 1.035372257 162.17623901 15.22515869 1.6597712 162.6832428 14.88186646 0.85851467 162.60391235 15.1647644
		 0.65490788 163.41297913 14.81936646 0.011539445 163.092773438 14.71659851 0.0079159308 164.11991882 14.61943054
		 1.56122041 166.40130615 13.78511047 1.82872033 166.48994446 14.19630432 1.706622 166.46217346 13.83905029
		 2.43121457 166.8959198 13.44276428 2.9182713 167.17701721 13.75372314 2.75590277 167.041046143 13.32090759
		 3.42211723 167.2215271 12.99765015 3.54204416 167.39996338 13.42126465 4.51257896 167.095031738 12.40943909
		 5.033226967 167.17082214 12.574646 4.97377872 167.57485962 12.63438416 5.3391366 167.58786011 12.32818604
		 5.33250713 168.63858032 11.94581604 3.71752977 170.37477112 12.21176147 4.66944122 170.25640869 11.62628174
		 3.6929388 172.036651611 11.26358032 4.43675375 171.76800537 10.85609436 4.53244066 172.77444458 9.98852539
		 3.88733149 172.85392761 10.4903717 3.89804626 173.59539795 9.86022949 2.77103567 173.20333862 11.048492432
		 2.90532756 174.36711121 9.97932434 2.95141912 175.31072998 8.94134521 2.14217424 174.96034241 9.96755981
		 2.51128411 175.71377563 8.75259399 1.71224344 175.68339539 9.13031006 1.5406121 176.59957886 7.6055603
		 1.25075912 176.256073 8.24963379 1.24878752 177.1499176 6.38934326 1.4916476 177.16293335 6.29205322
		 2.78546238 176.51699829 6.97525024 2.83740211 176.9989624 5.42398071;
	setAttr ".vt[166:331]" 1.48877025 177.56088257 4.91200256 2.64716983 177.43260193 3.53225708
		 1.49159861 177.75688171 3.78170776 1.2152046 177.59173584 4.85116577 1.24786818 177.79537964 3.44122314
		 1.61149001 177.81109619 2.18766785 1.2591114 177.80232239 1.77113342 1.12958872 177.89030457 2.82974243
		 1.14644003 177.79844666 3.84609985 0.97154075 178.077316284 2.21353149 1.14787436 177.86618042 1.75392151
		 1.0031298399 177.82736206 -0.17198181 0.057337433 178.70706177 1.47068787 0.055499107 178.70225525 3.089035034
		 -0.0070264037 178.72731018 1.46228027 0.038736504 178.29771423 -1.45367432 -0.01245709 178.3009491 -1.47486877
		 -0.9781248 177.83113098 -0.17759705 -0.91572791 177.25253296 -2.57305908 -0.46260053 177.35671997 -3.47016907
		 -0.89274418 176.52946472 -4.33358765 0.010020334 177.00044250488 -5.15188599 -0.82834923 175.88218689 -5.56422424
		 0.0098560862 176.19354248 -6.33985901 -0.22145435 174.43313599 -8.018295288 -1.056467175 174.50317383 -6.79196167
		 -1.049198151 172.93188477 -8.2648468 -1.18794358 174.48455811 -6.72790527 -1.16368115 175.0011444092 -6.041503906
		 -1.043123603 175.24436951 -5.90065002 -1.13713181 175.95739746 -4.77574158 -1.042426467 176.099868774 -4.67977905
		 -1.12925017 176.94555664 -2.65861511 -0.97370213 176.90028381 -3.21884155 -1.12916124 177.64361572 -0.14176941
		 -1.26064217 176.87940979 -2.67835999 -1.26527369 177.5798645 -0.13865662 -1.15308189 177.85969543 1.86637878
		 -1.2589283 177.80030823 1.74368286 -1.24153519 177.79164124 3.52407837 -1.13019156 177.83140564 3.46551514
		 -0.95860022 178.072555542 2.2183075 -0.94076747 177.90179443 4.43560791 -1.13865054 177.66389465 4.72062683
		 -1.22919953 177.16487122 6.36019897 -0.99976748 177.39628601 6.26791382 -1.17592347 176.39587402 8.013015747
		 -1.51348889 176.60186768 7.60542297 -1.46740162 177.16482544 6.28977966 -1.4714824 177.55899048 4.91818237
		 -1.27243149 177.59515381 4.78700256 -1.46566558 177.75804138 3.7900238 -1.58289719 177.81376648 2.18170166
		 -2.62763095 177.43249512 3.53286743 -2.54382682 177.509552 1.98220825 -2.46031141 177.40432739 0.37934875
		 -4.24147654 176.70327759 1.27909851 -4.34203005 176.65675354 2.45118713 -5.1325407 176.18893433 -0.099899292
		 -6.11117887 175.48435974 0.98809814 -6.15127563 175.44534302 -0.3956604 -5.23326731 176.011734009 -1.045333862
		 -2.63358116 177.046188354 -1.13835144 -1.51662385 177.3216095 -1.24046326 -1.47066116 177.67958069 0.53729248
		 -2.76571488 176.62211609 -2.49191284 -1.54159224 176.62464905 -3.3507843 -1.23931944 175.92471313 -4.78344727
		 -1.46209085 175.91680908 -4.81523132 -2.96989012 175.51515198 -4.85404968 -3.66228104 175.77149963 -3.88272095
		 -4.22849703 175.41052246 -3.99610901 -4.35379696 175.80484009 -3.11091614 -4.99621534 175.90945435 -1.92199707
		 -5.78649521 174.9377594 -3.053192139 -5.93464518 175.26622009 -1.97572327 -7.04703331 174.2726593 -1.98876953
		 -7.26703644 174.49203491 -0.32014465 -7.66518211 173.46066284 -1.89599609 -7.20921803 173.10617065 -3.072250366
		 -8.5247879 172.071029663 -1.91786194 -7.8949585 171.64898682 -3.70892334 -8.67381287 170.95358276 -3.12005615
		 -8.9171257 171.21748352 -2.067642212 -8.70152664 172.11157227 -1.17590332 -9.071718216 171.41256714 -0.943573
		 -9.053447723 171.6315155 -0.13156128 -9.072750092 170.83929443 -0.080978394 -8.91432953 170.9606781 1.083953857
		 -8.94363785 170.69979858 1.23587036 -8.47323418 170.82270813 1.51983643 -8.49268341 170.65263367 1.74984741
		 -8.23410988 170.99537659 2.0094909668 -8.41567612 170.97320557 1.60800171 -8.43568802 171.13630676 1.75111389
		 -8.75396729 171.24913025 1.68409729 -8.80530739 171.63795471 1.92318726 -8.42700577 171.43873596 4.10203552
		 -8.60589027 171.30635071 2.63465881 -8.30395126 171.12872314 2.24996948 -8.29921913 171.065429688 2.91717529
		 -8.19736481 170.98457336 2.36593628 -8.33627129 170.97073364 2.93730164 -8.2833271 171.15086365 3.41944885
		 -8.17725182 171.061508179 3.89031982 -8.29927254 170.92193604 3.6620636 -8.083068848 170.94009399 4.52822876
		 -8.49430847 170.74632263 4.037002563 -7.98582315 170.80805969 5.13044739 -8.074195862 170.60345459 5.4135437
		 -8.28676605 169.79367065 5.82925415 -9.029712677 169.70973206 3.25567627 -8.78291512 169.48190308 4.2454071
		 -9.41833687 169.30169678 1.23905945 -8.80851936 169.37237549 3.89329529 -8.20596886 169.051879883 6.4556427
		 -8.13965607 169.066879272 6.75398254 -7.47630835 168.36531067 8.39523315 -7.90920782 169.5736084 7.032974243
		 -6.9874959 169.35610962 9.001083374 -7.23530722 169.8679657 8.1930542 -7.50466108 170.30006409 7.11196899
		 -7.71245432 170.83622742 5.89515686 -7.37651491 170.59088135 7.0096588135 -7.47839975 170.77780151 6.65263367
		 -7.83088064 170.97631836 5.43782043 -7.43992567 170.85334778 6.97543335 -8.076154709 171.12849426 4.59745789
		 -8.1449852 171.29794312 5.33601379 -7.26169157 170.78256226 7.90480042 -7.22504473 170.65719604 7.37744141
		 -6.74737978 170.18495178 8.48188782 -7.039346218 170.3999939 7.71165466 -6.84158134 170.10115051 8.25061035
		 -6.74560833 170.11001587 8.4025116 -6.43096638 169.52508545 9.44026184 -6.37527275 169.28405762 9.55555725
		 -6.29303789 169.16194153 9.8187561 -6.79854679 170.2623291 9.092712402 -6.24428654 168.97486877 10.29589844
		 -6.13674402 168.37715149 10.33966064 -5.8117919 167.032104492 11.67584229 -5.92991161 167.070922852 11.25325012
		 -5.84223986 166.81747437 11.47618103 -6.34675837 167.8671875 10.41877747 -6.44425917 166.65586853 10.74386597
		 -6.86915398 166.91664124 9.83015442 -6.86789751 166.4513855 10.077972412 -6.83682108 166.35218811 10.13624573
		 -6.95105314 166.3425293 9.80993652 -7.038691044 166.22210693 9.7794342 -6.7265234 166.19200134 9.96307373
		 -7.55088282 165.81394958 9.29898071 -7.49939203 166.198349 9.41920471 -8.15781975 165.96955872 8.44763184
		 -7.68049002 166.6209259 8.89694214 -7.33229494 167.56381226 8.32705688 -8.062395096 167.73339844 7.3331604
		 -8.33369827 166.22476196 7.64663696 -8.41871452 165.98634338 7.58129883 -8.23155594 166.051879883 7.75405884
		 -8.14143372 165.65345764 7.68081665 -7.83563471 165.60858154 8.32640076 -8.22320366 166.08921814 8.031692505
		 -7.74668169 165.61857605 8.50808716 -7.7665658 165.50192261 8.47013855;
	setAttr ".vt[332:497]" -7.8994298 164.65264893 8.86526489 -8.025741577 165.3142395 8.052032471
		 -8.037490845 164.26034546 8.72946167 -7.61764479 163.86636353 9.71897888 -7.96497011 163.85925293 8.72372437
		 -8.094278336 164.23754883 8.19308472 -8.13566017 163.53710938 8.76701355 -8.34085274 164.33998108 7.64419556
		 -8.29713631 163.42982483 8.39466858 -8.08445549 163.22787476 8.92945862 -7.52224016 162.92726135 8.5308075
		 -8.064023972 163.10812378 9.046524048 -8.034236908 162.65214539 9.10426331 -7.58613348 162.49951172 9.062255859
		 -7.20364904 162.55493164 9.46746826 -7.016125202 164.14768982 9.0078887939 -6.7028513 163.95787048 9.77264404
		 -7.12167406 164.40065002 9.27674866 -7.22890329 164.64956665 8.18052673 -7.40365458 164.83108521 8.68557739
		 -7.3001771 165.2530365 8.16618347 -7.36744928 165.91513062 7.015136719 -7.69995928 165.47116089 6.27075195
		 -7.67274427 166.41471863 6.80613708 -7.42819834 166.28031921 7.54470825 -7.55783701 168.59939575 5.91244507
		 -7.1419692 168.15817261 7.13288879 -7.25193644 165.69287109 8.39836121 -7.51305342 165.44184875 8.59465027
		 -7.29608774 165.65454102 8.57051086 -6.95513582 165.85505676 9.25431824 -6.85880804 166.13565063 8.97962952
		 -6.19265795 166.31422424 10.071594238 -6.16646385 166.3449707 10.22674561 -5.74919081 166.53486633 10.65301514
		 -5.30426455 167.27398682 10.58996582 -5.15941811 166.74407959 11.1028595 -5.31084538 166.72973633 11.53970337
		 -4.9138937 166.88548279 11.84074402 -4.79556513 166.96478271 11.82762146 -4.51199532 167.062683105 12.30706787
		 -5.030348301 167.69033813 11.92868042 -4.15728092 167.60771179 12.41340637 -3.73510337 168.50569153 12.20297241
		 -2.27201056 167.71405029 13.47286987 -3.38208556 167.21453857 13.012268066 -2.56005192 166.97962952 13.38916016
		 -1.53178751 167.78236389 13.69267273 -2.15144396 166.82922363 13.54168701 -2.23353863 166.77964783 13.58558655
		 -1.51345313 166.35466003 13.79824829 -0.90998614 166.4841156 13.95022583 -0.20014901 165.39007568 14.19454956
		 0.0079159308 164.11991882 14.61943054 0.19651406 165.39613342 14.19892883 1.56122041 166.40130615 13.78511047
		 0.93810469 166.46670532 13.94488525 1.57264113 167.77589417 13.6849823 1.46596003 167.99725342 13.61967468
		 1.2984494 168.3127594 13.47344971 1.01703763 168.460495 13.46290588 0.8951391 168.11210632 13.57974243
		 0.65650189 166.97808838 14.018341064 0.22331643 166.8001709 14.29907227 0.037981991 166.69500732 14.34869385
		 0.19430716 166.16288757 14.19673157 -0.1663662 166.18955994 14.20176697 -0.2112323 166.79284668 14.29164124
		 -0.66997683 167.0076751709 13.98234558 -0.39848056 168.020202637 14.11402893 -0.017061481 167.22053528 14.49784851
		 -0.13087395 168.17829895 14.40240479 0.04956704 169.18486023 14.34301758 0.10766999 167.53771973 14.43145752
		 0.44652316 168.064605713 14.081222534 0.17708266 169.12113953 14.29396057 0.82936752 168.94599915 13.57676697
		 0.88258153 168.71359253 13.53947449 1.52654064 168.48225403 13.55937195 1.97973454 169.96182251 12.68534851
		 2.51454806 168.37518311 13.030807495 3.75670767 168.50430298 12.20210266 2.28360605 167.71914673 13.47386169
		 2.43121457 166.8959198 13.44276428 2.75590277 167.041046143 13.32090759 3.42211723 167.2215271 12.99765015
		 4.19011974 167.60456848 12.40675354 4.52119732 167.083007813 12.30888367 5.02971077 167.7210083 11.92800903
		 5.048155785 167.65531921 11.89071655 5.43420649 168.16137695 11.34448242 5.42450857 167.85255432 10.75526428
		 4.80256557 166.96585083 11.87632751 5.33080196 167.27565002 10.57121277 5.18103123 166.73983765 11.085021973
		 5.77066612 166.5408783 10.65397644 6.16365242 166.36149597 10.11001587 5.85312462 167.41607666 10.02545166
		 6.34082985 166.85116577 9.62446594 6.85634518 168.59260559 8.84077454 6.60438204 167.36929321 9.2146759
		 6.31786823 166.54676819 9.44537354 6.38754749 166.74752808 9.26535034 7.038087368 167.73887634 7.60690308
		 6.87590075 166.13415527 8.98503113 7.010036945 165.83485413 9.20625305 6.25527143 166.3729248 9.86625671
		 6.25270081 166.29289246 10.084732056 7.24425602 165.69607544 8.46214294 7.49965143 165.59106445 8.71255493
		 7.327456 165.32345581 8.16136169 7.52640057 165.46641541 8.60671997 7.59008074 165.28198242 8.57168579
		 7.41779232 164.83062744 8.6918335 7.24967337 164.63098145 8.18940735 7.14420462 164.39649963 9.29931641
		 7.04960537 164.15643311 8.96717834 7.69754314 163.071578979 8.074020386 7.52936649 162.91233826 8.56330872
		 7.22359896 162.51228333 9.48797607 7.54048109 162.49079895 9.15405273 6.39058447 161.47349548 11.57928467
		 6.47368288 163.80152893 10.38111877 6.0281353 163.70652771 11.2293396 6.20788765 161.51327515 12.0065917969
		 6.4410634 161.4513855 11.60733032 6.83141232 161.64241028 12.11660767 6.19526815 161.89416504 12.94265747
		 5.61095285 161.78485107 12.86312866 5.52159834 161.85714722 12.69445801 5.087795734 161.77278137 13.37191772
		 5.053062439 161.92437744 13.11439514 4.65613747 161.76333618 13.71014404 5.11323929 161.87130737 13.9344635
		 4.083234787 161.97483826 14.010513306 5.090801716 162.95223999 12.82063293 5.020629883 163.19285583 12.82958984
		 5.27894258 163.040222168 12.58776855 5.32689476 163.091567993 12.6572876 5.49280214 163.17192078 12.4879303
		 5.70183039 163.47010803 12.079620361 5.60572672 163.21847534 12.10020447 5.97744322 163.71717834 11.4415741
		 6.54631472 163.9803009 10.42980957 5.51231337 163.0075836182 12.64398193 5.53295708 162.91694641 12.77198792
		 5.27578545 163.26927185 13.013931274 5.39480639 163.03263855 13.57165527 4.31171608 163.25767517 13.89227295
		 3.91861892 163.31144714 14.065826416 3.71700168 163.25947571 14.10038757 3.59419727 163.10087585 14.087310791
		 5.16082287 162.17758179 13.93502808 5.81011915 162.40254211 13.23582458 5.26110077 162.40922546 13.74290466
		 5.28198433 162.63519287 13.76274109 5.39480639 163.03263855 13.57165527 5.76205158 162.82733154 13.046890259
		 6.05361414 162.92689514 12.8258667 6.33498621 163.13989258 12.48066711 7.34143448 162.36569214 10.94387817
		 7.1206212 162.85906982 11.1698761 7.14758778 162.97372437 10.42192078 7.52918911 162.57383728 10.37428284
		 7.68879557 162.40393066 10.12968445 7.65827227 163.21437073 9.94317627;
	setAttr ".vt[498:663]" 8.072629929 163.21226501 9.037780762 8.048736572 162.64355469 9.11985779
		 7.72671223 162.42959595 9.88839722 7.1261363 161.75750732 11.23027039 7.64929819 162.51429749 9.063964844
		 8.017360687 163.14604187 8.93676758 8.31592178 163.42970276 8.39627075 8.018253326 162.89683533 7.73306274
		 8.35497093 163.066558838 6.57073975 8.53405762 163.19778442 5.86045837 8.77338219 162.78683472 6.49206543
		 8.53951836 162.92713928 6.67207336 8.85218239 163.071884155 7.098831177 8.944561 162.53033447 6.2227478
		 8.79892731 163.11904907 5.70796204 9.15032578 162.74249268 3.80299377 8.42460442 164.53956604 5.65132141
		 7.89885426 165.10430908 6.045501709 7.71568251 165.47177124 6.27952576 8.012716293 165.52929688 6.052154541
		 7.69770765 166.41381836 6.78901672 8.065498352 165.61199951 5.98562622 8.27227592 165.75123596 4.72114563
		 8.55125046 164.86659241 3.70254517 8.73459435 165.7444458 0.86697388 8.31472206 167.94595337 2.93925476
		 8.47302246 168.25457764 0.97454834 8.45326424 168.51467896 0.0063781738 8.83908653 165.16416931 -0.27529907
		 8.3345089 168.18533325 -1.34448242 8.46551514 168.9828949 -0.86436462 8.2156868 168.56292725 -2.27462769
		 8.03494072 167.81237793 -3.38204956 7.94973707 169.14350891 -3.048233032 7.58992529 168.36004639 -4.65641785
		 7.79982853 166.8603363 -4.41589355 8.041423798 167.16807556 -3.26940918 7.77077007 166.37875366 -4.31242371
		 7.55499697 165.38867188 -5.23667908 7.6017499 164.96861267 -5.042282104 7.96388006 165.97891235 -4.1368103
		 7.91023064 165.10289001 -4.56871033 7.92029715 164.047714233 -4.79029846 7.49094391 162.87139893 -5.28779602
		 7.30774498 163.41899109 -5.67713928 7.10520411 162.38827515 -5.94096375 7.60787344 162.52929688 -5.34458923
		 7.984972 162.57151794 -4.93829346 6.63035393 162.46995544 -6.43785095 6.54619932 162.25386047 -6.82009888
		 6.40081978 162.86717224 -6.98326111 6.69006443 163.48384094 -6.41397095 7.020693779 164.99461365 -5.9931488
		 6.7307744 164.71470642 -6.46572876 6.51252747 163.68444824 -7.090927124 6.69690275 164.69378662 -7.28089905
		 6.58399153 164.38232422 -7.5479126 6.86193991 165.87097168 -7.15377808 6.77636862 165.51481628 -6.62045288
		 7.24478865 167.17546082 -5.76707458 7.36390305 166.62393188 -5.42982483 7.32094193 167.58668518 -6.037109375
		 7.32000065 168.68774414 -6.2003479 7.14472818 168.24584961 -6.50050354 7.25129414 168.84547424 -6.23231506
		 6.8784852 169.017913818 -6.28637695 6.57278395 167.91778564 -6.87954712 6.30992889 168.59913635 -6.81599426
		 5.8357892 167.39398193 -7.39894104 6.3089962 166.84843445 -7.23451233 6.68611717 166.52282715 -7.27363586
		 6.78323364 166.57698059 -7.21846008 6.64132643 165.04598999 -7.48724365 6.53040028 164.90733337 -7.5716095
		 6.14010477 165.19606018 -7.49729919 6.39319134 164.30755615 -7.64295959 5.96479225 162.53443909 -7.47018433
		 6.11006975 162.61485291 -7.34950256 5.96695948 162.26899719 -7.45840454 5.31863976 163.55895996 -7.66854858
		 4.78661919 162.11418152 -7.91371155 4.23882198 164.2644043 -8.15391541 4.25866699 162.10983276 -8.12794495
		 3.25405192 164.064483643 -8.51695251 3.35250497 162.042037964 -8.40319824 2.52221251 163.30152893 -8.69747925
		 2.54429913 162.15863037 -8.59385681 2.45418072 162.67071533 -8.74118042 2.28605294 163.33319092 -9.28263855
		 1.95183122 162.30001831 -9.38916016 2.10870242 163.09262085 -9.38291931 1.83912885 164.6491394 -9.53126526
		 1.49175453 163.66622925 -9.53468323 1.41540587 162.50733948 -9.39161682 1.015670061 163.28027344 -9.039505005
		 1.26599443 165.40170288 -9.18370056 0.75689995 164.14596558 -8.97821045 1.10159671 162.071762085 -8.96963501
		 0.83645022 161.40298462 -8.83221436 1.2144146 161.57510376 -8.9223938 0.33602783 160.97093201 -8.82017517
		 0.0077740503 160.58078003 -8.9680481 0.96646142 161.22003174 -9.16152954 1.3145417 161.50334167 -9.45890808
		 2.00021839142 161.83103943 -8.84718323 1.87277842 162.071456909 -9.17955017 2.130656 162.03012085 -8.80155945
		 2.21529484 161.85375977 -8.76147461 0.92675954 161.18159485 -9.75318909 0.0089684082 160.57495117 -9.79193115
		 -0.855946 161.14337158 -9.77914429 -0.95962113 161.23504639 -9.1415863 -1.16121197 161.55258179 -8.9226532
		 -1.27612567 161.49038696 -9.48667908 -1.57380271 161.69104004 -8.88085938 -1.24965191 161.73730469 -9.022476196
		 -1.38616824 162.66688538 -9.4065094 -0.97030473 163.1605072 -9.0085754395 -1.44031024 163.83901978 -9.49816895
		 -1.54716015 163.68789673 -9.53208923 -1.47134876 162.534729 -9.42320251 -1.92888117 162.29673767 -9.39051819
		 -1.77247167 162.079681396 -9.24159241 -2.0036711693 162.35675049 -9.31272888 -2.28722763 163.27101135 -9.25035095
		 -2.16573763 164.29338074 -9.42303467 -2.25736141 164.38224792 -9.30943298 -2.25394225 165.63591003 -8.97680664
		 -2.42411256 164.89242554 -8.98049927 -2.71645236 165.057891846 -8.75117493 -2.48615861 163.4533844 -8.70921326
		 -3.2284956 164.056228638 -8.51966858 -3.29525709 162.058761597 -8.41429138 -4.17540693 162.11645508 -8.15168762
		 -2.0091862679 161.84284973 -8.83041382 -4.70462561 162.0099639893 -8.14044189 -4.87520409 162.12431335 -7.86907959
		 -4.21050835 164.2406311 -8.15760803 -5.29977083 163.55114746 -7.66850281 -5.53010035 165.57843018 -7.60609436
		 -5.86470842 164.1230011 -7.53388977 -6.12953043 165.20802307 -7.49575806 -6.43456125 164.45199585 -7.65237427
		 -6.70137262 166.43234253 -7.28111267 -6.28370428 166.89042664 -7.23521423 -6.5495882 167.96331787 -6.86802673
		 -7.089727879 167.96377563 -6.6114502 -7.086368084 167.22320557 -6.77433777 -7.29923105 167.58633423 -6.040679932
		 -6.85577965 165.93119812 -7.1295929 -7.23031569 167.17955017 -5.75534058 -6.75760174 165.51020813 -6.59594727
		 -6.71225405 164.70968628 -6.46607971 -6.67593336 164.68792725 -7.28216553 -6.49145603 163.668396 -7.091949463
		 -6.59584379 164.54171753 -7.55361938 -6.21944904 163.23777771 -7.48796082 -5.97351646 162.73570251 -7.48835754
		 -6.12533903 162.81529236 -7.3825531 -5.93911219 162.29742432 -7.4629364 -6.37787676 162.8598175 -6.9899292
		 -6.54644871 162.25869751 -6.79460144 -6.14706373 162.13859558 -7.59825134 -6.97521353 162.25575256 -7.46594238
		 -6.98639917 162.35169983 -7.15826416 -7.034653187 162.36988831 -7.040023804;
	setAttr ".vt[664:829]" -7.27756453 162.34602356 -6.87713623 -7.33098936 163.76402283 -6.81459045
		 -7.14655352 163.45230103 -6.93025208 -7.05927515 164.54745483 -7.0098571777 -7.17201757 164.66410828 -6.85964966
		 -7.11164141 164.85795593 -7.067886353 -7.020323277 163.064376831 -7.52290344 -7.25590563 165.55764771 -7.2116394
		 -7.15725279 164.60455322 -7.5032959 -6.61074352 162.37252808 -8.1918335 -6.092293262 162.11553955 -8.37557983
		 -6.88576603 164.44125366 -8.22073364 -6.34632111 165.50114441 -8.24580383 -5.56594753 164.30856323 -8.57551575
		 -5.35078239 162.015853882 -8.7048645 -5.12111473 162.21844482 -8.74671936 -4.89211798 162.39704895 -8.94963074
		 -4.53310966 162.2724762 -8.66471863 -4.070861816 161.9808197 -8.51330566 -3.92846584 161.92581177 -8.42376709
		 -3.99021912 161.86174011 -9.18559265 -2.066698551 161.76855469 -9.38056946 -1.99884439 161.80004883 -9.52459717
		 -3.73401976 161.93049622 -9.24978638 -3.19753695 163.63269043 -9.48861694 -1.63370395 162.59516907 -9.77020264
		 -1.32075191 161.84454346 -9.70858765 -1.26146781 166.17140198 -10.0059051514 -0.97323108 162.93043518 -9.98370361
		 -1.67612791 161.63336182 -9.43966675 0.0077872444 161.9723053 -10.56544495 0.0074009513 163.95483398 -10.72360229
		 0.0090215495 165.82785034 -10.95968628 0.99595463 162.85231018 -9.9707489 0.96505803 166.20013428 -10.38778687
		 1.24525321 166.17208862 -10.04800415 1.23985803 164.97198486 -9.95663452 1.33764946 166.19128418 -10.0020446777
		 1.36607277 161.83624268 -9.70474243 1.64708054 162.58865356 -9.77444458 4.035633087 161.86248779 -9.17996216
		 2.079599857 161.76133728 -9.42149353 1.3145417 161.50334167 -9.45890808 2.00021839142 161.83103943 -8.84718323
		 0.92675954 161.18159485 -9.75318909 0.26795617 160.9588623 -10.098556519 -0.22259958 160.89982605 -10.087814331
		 2.21529484 161.85375977 -8.76147461 3.99740982 161.91639709 -8.52041626 4.16357517 161.9604187 -8.36251831
		 4.23371124 162.080215454 -8.55825806 4.74048328 162.0066375732 -8.12394714 4.78661919 162.11418152 -7.91371155
		 6.23858452 162.1428833 -7.5664978 5.96695948 162.26899719 -7.45840454 6.54619932 162.25386047 -6.82009888
		 6.9968133 162.25756836 -7.45539856 7.017319202 162.35728455 -7.069732666 7.26496601 162.35075378 -6.90423584
		 7.6892395 162.36891174 -6.32209778 7.10520411 162.38827515 -5.94096375 7.55148458 162.50810242 -5.65235901
		 7.60787344 162.52929688 -5.34458923 7.80481482 162.70726013 -5.61167908 8.32978821 162.47805786 -5.21917725
		 7.984972 162.57151794 -4.93829346 8.58390045 162.53396606 -3.97966003 8.470541 162.65008545 -3.91360474
		 9.032814026 162.73953247 -1.97512817 9.6889534 162.81022644 -2.3150177 9.044563293 163.16593933 -1.55685425
		 9.60743141 163.48677063 -1.7361145 9.72920036 163.61294556 -1.98997498 9.85258675 163.8011322 -0.99232483
		 9.54688644 163.73971558 -0.81881714 9.94826508 163.61984253 0.046417236 9.69659042 164.88569641 -0.46707153
		 9.43607521 165.70233154 -2.12612915 9.3711834 167.72494507 -0.6295929 9.19408607 167.51277161 -1.87919617
		 9.038805008 166.48231506 -3.36791992 9.19177628 164.016998291 -3.82272339 9.44913864 162.84771729 -3.29956055
		 9.056125641 162.8500061 -4.44003296 9.079900742 162.59936523 -4.10757446 9.49047089 162.76516724 -3.0090484619
		 9.30964279 162.70567322 -3.013427734 8.54269791 162.73199463 -5.38674927 8.43124771 162.5861969 -5.3144989
		 7.87498283 162.82821655 -5.56820679 8.62003326 163.17016602 -5.33334351 7.96856022 163.44099426 -5.35699463
		 7.85115099 163.47219849 -5.43615723 8.01449585 164.15408325 -5.30258179 7.78533506 163.68534851 -5.5223999
		 8.068078995 164.61251831 -5.23745728 8.68192291 164.72813416 -4.92736816 8.48309898 165.95828247 -4.44271851
		 8.5473156 166.47117615 -4.11123657 8.48220634 166.44850159 -4.24751282 8.93457794 167.71951294 -2.24134827
		 9.10728073 168.37844849 -0.81773376 8.85029984 167.71177673 -2.53703308 8.98332596 168.29086304 -1.78004456
		 9.42479706 168.80999756 -0.80812073 9.29857826 168.6275177 -1.33544922 9.3139019 168.70666504 -1.48466492
		 9.17480469 168.92277527 -2.21699524 9.18255424 168.37564087 -2.29116821 9.053413391 167.89015198 -3.20184326
		 8.95193672 167.96466064 -2.55386353 8.5791626 166.94647217 -3.91696167 8.67996979 167.2039032 -3.25764465
		 8.75132179 167.01574707 -4.39398193 8.22130394 165.87767029 -4.80639648 8.11903191 165.215271 -5.02482605
		 7.92570114 164.58529663 -5.50115967 8.2702198 165.64929199 -5.50468445 7.96069145 164.026031494 -6.074462891
		 7.82493925 162.89451599 -5.66885376 7.87680769 162.66421509 -6.23370361 7.53059244 165.17176819 -6.64241028
		 8.27111244 165.71658325 -5.56048584 7.7695179 166.15934753 -6.32304382 7.73363495 166.67160034 -6.42530823
		 8.031339645 167.43721008 -5.76834106 8.74650383 167.062896729 -4.44979858 8.98991966 167.76832581 -3.56878662
		 8.39965057 168.59487915 -4.5921936 8.91525841 170.092712402 -2.32138062 8.43517303 169.44392395 -4.56642151
		 8.047218323 167.99913025 -6.076568604 8.11909485 169.32992554 -6.0066070557 7.89474678 168.62921143 -6.67796326
		 7.66004372 166.87619019 -7.040588379 7.64800596 167.70191956 -7.18009949 7.09419632 165.51248169 -8.064422607
		 7.59202528 167.83987427 -7.23144531 6.98302126 167.11909485 -7.81202698 6.32415152 168.14279175 -8.087738037
		 5.31736565 168.20042419 -8.68109131 5.4202013 166.47949219 -8.7164917 6.34922647 165.47650146 -8.24641418
		 5.5886488 164.35826111 -8.57038879 6.047131062 162.10606384 -8.39764404 6.19363832 162.35426331 -8.35771179
		 6.38378191 162.23902893 -8.25973511 6.61650896 162.38467407 -8.22528076 7.13840055 164.84762573 -7.6652832
		 7.050924301 163.2387085 -7.510849 7.084325314 164.53051758 -7.028717041 7.28392696 165.54229736 -7.30587769
		 7.25674677 165.4756012 -7.55291748 7.30049419 165.84526062 -6.73526001 6.8779254 164.51306152 -8.22143555
		 5.3555088 162.019546509 -8.71342468 5.22190094 163.62536621 -8.67697144 5.13134718 162.21681213 -8.74801636
		 4.94407272 162.39022827 -8.92562866 4.87732887 164.74069214 -8.96536255 4.58623695 162.83033752 -9.1116333
		 4.48027039 162.29704285 -9.10653687 4.11880684 162.88519287 -9.27816772 3.13658047 163.75544739 -9.51023865
		 3.58435726 165.44534302 -9.46717834 4.11596012 165.95381165 -9.31452942;
	setAttr ".vt[830:995]" 4.5987587 166.3487854 -9.13052368 3.45169497 167.77380371 -9.63293457
		 4.13923264 168.23405457 -9.29951477 5.29475927 165.49468994 -8.71618652 4.13415241 169.28910828 -9.15328979
		 5.63517523 168.90985107 -8.34889221 4.56779099 169.99075317 -8.68840027 4.55331993 170.75086975 -8.3817749
		 2.8214035 170.57318115 -9.1905365 2.9065485 171.54312134 -8.69929504 1.61719179 171.033981323 -9.31730652
		 2.054582357 171.9967041 -8.66246033 1.55052328 172.39328003 -8.60974121 2.2995472 173.56568909 -7.46972656
		 1.61724937 174.059417725 -7.24371338 2.61267257 174.7098999 -6.21432495 1.52975082 174.78952026 -6.4176178
		 1.26463544 174.42869568 -6.79415894 1.2444936 175.91101074 -4.80381775 1.15306532 175.94728088 -4.80455017
		 1.26996386 176.86680603 -2.70915222 1.11671162 176.95718384 -2.69915771 1.070331335 176.024703979 -4.80506897
		 1.066756845 174.89752197 -6.33834839 1.14862049 174.51283264 -6.72764587 1.035349727 174.4980011 -6.85012817
		 1.16741693 172.90879822 -8.20429993 1.082951188 172.91481018 -8.26094055 0.23884436 174.42396545 -8.029067993
		 0.83127671 175.89442444 -5.57214355 0.0076493649 173.24780273 -9.13900757 0.72972435 172.11088562 -9.27163696
		 0.19662493 171.038024902 -10.20889282 -0.13647342 171.060409546 -10.22123718 -0.70302701 172.12217712 -9.27099609
		 -0.67481709 170.77532959 -9.96821594 -0.83103997 169.5249176 -10.27737427 -1.050707817 171.220047 -9.37164307
		 -1.13578629 169.22174072 -9.95187378 -1.24503398 169.19299316 -9.86096191 -1.27420747 167.51734924 -10.016555786
		 -1.17358315 167.56210327 -10.092987061 -0.94315159 166.15478516 -10.38804626 -0.70160168 168.3994751 -10.56546021
		 0.010757779 167.80783081 -11.0337677 0.0041147997 169.29560852 -10.83387756 0.7276774 168.44522095 -10.5546875
		 0.85298616 169.51986694 -10.27264404 1.14329648 169.21678162 -9.96313477 1.22227395 167.69775391 -10.051712036
		 1.24778855 169.21551514 -9.86022949 1.37349689 169.27035522 -9.81105042 1.35362172 167.78672791 -10.0031280518
		 1.67606306 168.348526 -9.99760437 1.55032361 166.13523865 -9.99601746 2.62222385 167.51676941 -9.85639954
		 2.43593502 165.41007996 -9.74897766 2.48604059 168.69537354 -9.82566833 1.58807147 170.24996948 -9.63008118
		 2.65700126 169.60006714 -9.58554077 1.30247235 170.66772461 -9.42422485 1.26418698 171.33172607 -9.21554565
		 1.10126793 171.23376465 -9.33029175 1.22712731 170.3196106 -9.53263855 0.68401909 170.75325012 -9.98770142
		 -1.51919019 166.13000488 -9.99838257 -1.66713607 168.35275269 -9.99584961 -1.36904168 169.20065308 -9.83061218
		 -1.57311463 170.24966431 -9.62905884 -1.29447818 170.66094971 -9.4303894 -1.25272489 171.33117676 -9.21458435
		 -1.17277503 171.24978638 -9.27732849 -1.15731359 172.91346741 -8.20446777 -1.5311749 172.38742065 -8.61428833
		 -1.59682214 174.056350708 -7.24665833 -2.27081609 173.5741272 -7.46578979 -2.59531331 174.71034241 -6.21311951
		 -1.50502098 174.7988739 -6.40751648 -3.55004907 173.3130188 -7.086410522 -3.30260205 174.81213379 -5.63725281
		 -4.60145712 173.5634613 -6.027999878 -4.80207109 172.27888489 -6.92533875 -5.75003481 172.52839661 -5.77711487
		 -6.23235798 171.73114014 -6.037780762 -5.85794544 170.87878418 -7.14898682 -4.90723324 171.074523926 -7.76712036
		 -5.37235403 170.20211792 -7.95346069 -4.66431522 169.84460449 -8.5806427 -4.26068068 170.50500488 -8.49153137
		 -2.80207276 170.56924438 -9.19165039 -4.61205578 168.71472168 -8.96858215 -5.81178284 168.80329895 -8.28659058
		 -5.86212397 168.35557556 -8.37782288 -7.62341356 167.83374023 -7.19326782 -6.87823057 168.75500488 -7.48057556
		 -6.4019351 169.45805359 -7.53196716 -6.97779799 169.66729736 -6.91993713 -7.85799646 168.5652771 -6.71208191
		 -7.95978212 169.42597961 -6.079162598 -8.12219048 169.2850647 -5.90855408 -8.03074646 168.0047302246 -6.067672729
		 -7.64233828 166.86131287 -7.03326416 -7.082746983 165.57507324 -8.047088623 -7.28249979 165.70721436 -7.51187134
		 -7.29787874 165.90937805 -6.77133179 -7.70903826 166.66082764 -6.44120789 -7.32001925 165.84327698 -6.70425415
		 -7.74108839 166.11668396 -6.33714294 -7.51137877 165.10635376 -6.64433289 -7.1257062 164.88990784 -6.92750549
		 -7.93948889 164.0026245117 -6.074478149 -8.25357628 165.71730042 -5.55714417 -8.25991631 165.66931152 -5.48796082
		 -7.91842604 164.64701843 -5.49832153 -7.76650095 163.70016479 -5.54019165 -7.90098429 164.066955566 -5.36613464
		 -7.95529032 164.61090088 -5.36755371 -8.20127296 165.87202454 -4.81829834 -8.21778107 165.78642273 -4.69741821
		 -8.083086014 164.53083801 -5.25128174 -8.36097527 165.98788452 -4.4803772 -8.70818138 165.13371277 -4.70410156
		 -8.37088013 164.10560608 -5.26603699 -7.9865489 163.40493774 -5.35664368 -7.82631159 163.065719604 -5.51760864
		 -7.89837313 162.76399231 -5.57313538 -7.80663824 162.84197998 -5.68002319 -7.78838778 162.69499207 -5.60261536
		 -8.52804565 162.69761658 -5.36952209 -8.60054207 163.27804565 -5.32392883 -9.036380768 162.84158325 -4.44285583
		 -9.07998848 162.60345459 -4.077804565 -9.43266296 162.84988403 -3.29211426 -9.67550659 162.81552124 -2.31307983
		 -8.59668732 162.54431152 -3.87101746 -9.0048904419 162.73043823 -1.99812317 -8.4533844 162.66543579 -3.90483093
		 -8.80220604 164.11630249 -2.14759827 -9.027587891 163.18635559 -1.52781677 -8.97687721 163.87911987 -1.37626648
		 -9.12661362 163.52970886 -0.68922424 -9.63397408 163.49282837 -1.78535461 -9.52173805 163.73794556 -0.81855774
		 -9.93129158 163.61099243 0.048828125 -9.24990273 163.22663879 0.0082397461 -8.81950378 165.16572571 -0.27885437
		 -9.32302094 162.94927979 1.034164429 -9.027935028 163.96784973 1.22132874 -8.53290176 164.8657074 3.69873047
		 -8.71548271 165.74497986 0.86616516 -8.25303841 165.75224304 4.72216797 -8.39957428 164.56861877 5.64334106
		 -8.042100906 165.60998535 6.0042114258 -8.31397057 164.616745 5.74163818 -7.96559 165.58473206 6.095977783
		 -8.0068244934 164.8344574 5.91661072 -8.51261711 163.18885803 5.87599182 -8.71087837 163.15846252 5.75474548
		 -8.74609184 162.78201294 6.48059082 -8.78506851 163.12640381 5.66505432 -8.91959 162.53181458 6.2192688
		 -8.83031845 163.074401855 7.11534119 -9.54698563 162.79214478 6.62457275 -9.58453941 162.5826416 5.98197937
		 -9.66658592 162.67494202 5.53833008 -9.60936165 162.67041016 5.074554443;
	setAttr ".vt[996:1161]" -9.1774807 162.67106628 4.63581848 -9.12800789 162.74121094 3.83370972
		 -9.032852173 162.70346069 4.7354126 -9.89608002 162.83078003 3.70079041 -9.51169014 162.88616943 0.48654175
		 -9.41369438 162.91395569 0.54881287 -9.94178772 163.13117981 0.49386597 -10.0082092285 163.068527222 0.60025024
		 -9.93873024 163.52362061 0.32662964 -9.82403374 163.94851685 1.23323059 -10.034965515 163.07182312 1.5397644
		 -9.92768669 162.99505615 2.89649963 -9.93677711 162.88264465 2.55757141 -9.99419975 162.9087677 2.39076233
		 -10.035535812 162.94540405 1.44769287 -9.41539001 164.48403931 3.68873596 -9.17777061 164.94868469 5.1078186
		 -8.86741829 165.61727905 6.33876038 -8.54656982 165.3144989 7.88226318 -8.52654648 165.635849 7.56173706
		 -8.18930054 165.35871887 7.89257813 -8.048599243 165.61373901 7.85900879 -8.089347839 164.93966675 7.69300842
		 -7.91872835 164.79777527 7.82069397 -7.96104956 164.65837097 7.74995422 -8.48080063 164.40690613 7.54554749
		 -8.60926437 163.90800476 7.38136292 -8.91475105 163.91941833 7.39569092 -8.79142761 163.57206726 7.27856445
		 -8.6429081 163.5005188 7.36383057 -8.51003647 162.92964172 7.77249146 -7.98746538 162.89517212 7.73667908
		 -7.67962027 163.076034546 8.072280884 -8.49954605 162.92549133 6.68608093 -8.28364372 167.99575806 6.26803589
		 -7.834764 168.23492432 6.96917725 -8.37856102 168.61398315 4.65151978 -8.49872208 168.74569702 3.94602966
		 -8.20616531 168.74523926 5.003036499 -8.32723427 168.9299469 4.58262634 -8.28476524 168.98426819 5.098205566
		 -7.75167227 168.48808289 6.91114807 -7.29804564 167.82757568 8.27159119 -7.24456072 167.8215332 8.49198914
		 -6.82277155 166.90501404 9.34692383 -6.85620165 166.7820282 9.26260376 -6.98180342 166.63621521 9.26138306
		 -8.46926689 169.076934814 4.21316528 -8.93945885 168.88458252 1.89996338 -8.86697578 168.70455933 2.17214966
		 -9.080522537 168.44497681 0.12219238 -9.099365234 168.65109253 0.068389893 -9.091659546 168.39358521 -0.782547
		 -9.35291862 167.72183228 -0.62860107 -9.38390541 167.85531616 0.13786316 -9.28160667 167.9744873 1.39382935
		 -9.55504227 165.50267029 0.38986206 -9.36487198 165.48924255 2.053939819 -9.6783123 164.88153076 -0.46502686
		 -9.87923813 163.72639465 -0.4367981 -9.828125 163.81359863 -1.022750854 -9.41718292 165.70217896 -2.12452698
		 -9.69614029 163.64376831 -2.03666687 -9.02110672 166.48927307 -3.36036682 -9.17241096 164.015914917 -3.82391357
		 -8.47278214 166.47160339 -4.1927948 -9.17456436 167.51234436 -1.88267517 -8.84976006 167.75761414 -2.35877991
		 -8.96825981 168.31376648 -1.71478271 -9.40378761 168.78704834 -0.85147095 -9.1432991 168.70596313 -0.19229126
		 -9.45661736 169.11715698 0.023757935 -9.19560051 169.954422 -1.036499023 -9.15097618 168.91482544 -2.24920654
		 -9.18028259 168.41944885 -2.21859741 -8.9766674 167.63713074 -3.62382507 -8.90809059 167.9083252 -2.64027405
		 -8.56332588 166.98538208 -3.85578918 -8.74530983 167.034072876 -4.41867065 -8.379879 168.60411072 -4.58894348
		 -8.010284424 167.43345642 -5.77090454 -8.41447449 169.4384613 -4.57414246 -8.89619827 170.091674805 -2.32325745
		 -9.13308334 169.88682556 2.17927551 -9.039405823 168.97802734 1.69522095 -9.025949478 166.42900085 4.12667847
		 -9.02264595 168.098327637 2.94425964 -8.88788033 168.59043884 2.19496155 -8.62291527 167.5269165 5.2301178
		 -8.0045681 168.19892883 4.55741882 -8.29422188 167.95095825 2.9462738 -8.4520874 168.27101135 0.98617554
		 -8.43421936 168.51551819 0.0070648193 -8.32984543 168.1730957 -1.23190308 -8.68500519 165.67079163 -1.10673523
		 -8.54133987 166.21720886 -1.56613159 -8.18120193 167.8571167 -2.19508362 -8.19650841 168.55488586 -2.26600647
		 -8.01559639 167.81417847 -3.38241577 -8.025642395 167.16137695 -3.26081848 -7.78167009 166.86659241 -4.41104126
		 -7.74887991 166.37121582 -4.3327179 -7.53922892 165.37695313 -5.23265076 -7.57949114 164.99113464 -5.039077759
		 -7.94579458 165.96910095 -4.1373291 -7.89005136 165.13293457 -4.56144714 -7.89658976 164.10292053 -4.79086304
		 -7.46228361 162.82872009 -5.30525208 -7.29327631 163.42793274 -5.67225647 -7.07785368 162.39093018 -5.95167542
		 -6.60965586 162.48573303 -6.44003296 -7.006336689 164.99443054 -5.98599243 -6.66623592 163.48944092 -6.42533875
		 -7.34489012 166.62020874 -5.42973328 -7.6637702 162.37097168 -6.30834961 -7.51394987 162.49830627 -5.66665649
		 -7.64682055 162.52822876 -5.31124878 -8.28612137 162.48226929 -5.21972656 -8.0069885254 162.58059692 -4.85279846
		 -7.85713434 162.65698242 -5.0098266602 -7.86015177 162.64814758 -6.23594666 -8.40731049 163.97781372 -3.60546875
		 -7.57000399 168.34381104 -4.66349792 -7.91708899 169.094390869 -3.1217041 -7.53858328 169.29208374 -4.80081177
		 -7.29692698 168.67950439 -6.08380127 -7.63904333 170.5428009 -3.9413147 -7.3453002 169.81489563 -5.11657715
		 -7.13472414 168.85450745 -6.18611145 -6.57147026 168.88204956 -6.47735596 -6.6348176 169.724823 -5.84194946
		 -5.7437067 169.88911438 -6.53483582 -5.73987484 168.90553284 -7.094924927 -5.072772026 170.19796753 -6.93154907
		 -4.64701128 171.31632996 -6.4609375 -3.94110799 170.61706543 -7.54374695 -4.72331953 169.63314819 -7.5135498
		 -3.91639733 169.52359009 -8.06048584 -4.70361757 168.64002991 -7.83369446 -3.92821765 168.53079224 -8.29190063
		 -3.049995184 169.30792236 -8.5788269 -2.9527986 170.26873779 -8.3245697 -2.27771211 171.12283325 -8.64216614
		 -2.7205112 171.20030212 -8.028442383 -2.22002649 171.84942627 -7.78840637 -1.62181735 171.66213989 -8.091629028
		 -1.9819622 170.79953003 -8.8525238 -2.33172107 170.10971069 -9.04057312 -1.86925101 169.39405823 -9.22792053
		 -2.4350009 168.84222412 -9.22209167 -1.95320141 168.16453552 -9.34721375 -1.20730364 168.47354126 -9.12910461
		 -1.18698871 166.9513092 -9.16078186 -2.23474216 167.69151306 -9.30625916 -2.033981562 166.29110718 -9.04826355
		 -1.61469471 165.6950531 -9.19685364 -2.81536722 166.72535706 -8.84362793 -1.82864761 164.68395996 -9.52996826
		 -1.24254739 165.3938446 -9.18685913 -0.926247 166.089141846 -9.28669739 -0.50858521 167.31105042 -9.50672913
		 -0.77855414 168.47654724 -9.43649292 0.018310862 168.43182373 -9.6421051 0.0096210428 166.2157135 -9.47920227
		 0.52820033 167.29084778 -9.50514221 0.95817095 166.042160034 -9.27644348;
	setAttr ".vt[1162:1327]" 1.20554698 166.96994019 -9.1633606 1.63644111 165.70703125 -9.19354248
		 2.28044486 165.62579346 -8.97749329 2.052158117 166.31938171 -9.051513672 2.82412124 166.75018311 -8.84985352
		 2.75707078 165.066207886 -8.75238037 2.41330671 164.7741394 -9.028717041 2.14613533 164.26887512 -9.42611694
		 4.14330006 166.062072754 -8.32302856 3.22713375 167.98616028 -8.69252014 2.25188804 167.69007874 -9.30702209
		 2.45685363 168.83947754 -9.22134399 1.96867359 168.15922546 -9.34686279 1.22864604 168.53533936 -9.12156677
		 1.88506031 169.38513184 -9.22859192 1.1795392 169.61482239 -8.94448853 0.82448304 169.73547363 -9.23788452
		 0.79494536 168.48678589 -9.43693542 0.29034895 169.35462952 -9.50805664 0.0068545649 170.090194702 -9.37818909
		 -0.26749247 169.28634644 -9.51605225 -0.7984516 169.72674561 -9.24424744 -1.1664207 169.62254333 -8.94195557
		 -1.1744225 171.096633911 -8.45826721 -0.68959033 171.18333435 -8.75343323 -1.15560389 172.35148621 -7.65797424
		 -0.60417444 172.45823669 -7.92687988 0.011707902 171.19822693 -8.91764832 0.71003997 171.17514038 -8.75744629
		 0.6245662 172.45802307 -7.92680359 1.17906415 172.35395813 -7.65486145 1.19290495 171.10948181 -8.44950867
		 1.63282657 171.65988159 -8.089385986 2.22813177 171.84075928 -7.79971313 2.28495598 171.1118927 -8.65779114
		 2.74061441 171.23486328 -8.006149292 2.98328805 170.30679321 -8.30392456 3.070195913 169.30288696 -8.57835388
		 3.76778197 169.65454102 -8.20648193 3.98830676 170.59040833 -7.73233032 4.88781643 169.48614502 -7.6782074
		 5.10134315 170.15116882 -7.22720337 4.42829943 171.44259644 -6.9214325 5.62920284 170.65356445 -6.41178894
		 6.44421625 169.60925293 -6.20388794 6.6850915 170.43077087 -5.33782959 6.43460655 171.62760925 -4.84700012
		 5.93314505 172.31088257 -4.83848572 7.082379818 172.4082489 -3.8865509 7.53119564 171.25299072 -3.78495789
		 7.072882175 170.91114807 -4.42446899 7.72828865 170.70449829 -3.99797058 7.99415445 170.88064575 -3.25753784
		 7.78255987 170.63336182 -3.93457031 7.41541195 169.63671875 -5.49230957 7.49017572 169.69145203 -5.25714111
		 7.55969477 169.28918457 -4.79394531 8.042648315 170.36967468 -2.16870117 8.17944527 169.89672852 -1.8986969
		 8.2554512 169.36576843 -1.98750305 8.76374245 169.5406189 -1.1918335 8.63625336 170.015396118 -1.11779785
		 8.85198212 169.88735962 -0.28501892 8.73174095 170.45184326 0.19680786 8.8612175 169.86038208 1.20191956
		 8.85591125 169.42098999 1.16091919 8.70372963 169.47241211 2.89558411 8.72693634 169.8061676 2.29200745
		 8.6453476 169.76821899 3.42922974 8.53029633 169.56672668 3.88841248 8.53846169 169.39263916 3.3888092
		 8.55269814 169.10249329 1.37013245 8.28173447 169.19552612 3.37078857 8.45669556 168.7454071 0.97319031
		 8.60283089 169.1855011 0.28266907 8.47613525 169.24568176 -1.44929504 8.31193733 168.82344055 2.40351868
		 8.022386551 168.21075439 4.5536499 7.91361856 168.87176514 4.51872253 7.5782733 168.59753418 5.91049194
		 7.63047934 168.96504211 6.86299133 7.95903111 169.073226929 5.10968018 7.81117392 169.084503174 6.20941162
		 7.92527056 169.38247681 6.14050293 7.52972174 169.043640137 7.32647705 7.47171211 168.87695313 7.47131348
		 7.0033764839 168.31259155 8.58322144 6.99771023 168.25338745 8.51971436 6.9923687 169.35264587 8.16828918
		 7.18681002 169.78361511 7.43019104 7.028673649 169.76182556 7.69812012 6.6605711 168.95977783 8.9254303
		 6.40701866 169.094833374 8.94789124 6.78427696 169.84164429 7.98400879 7.099267483 170.15670776 7.23242188
		 6.80301094 170.25695801 7.47793579 6.13042021 169.4987793 8.96820068 6.092046261 169.52670288 9.027206421
		 6.72241735 170.28715515 7.81559753 6.69491816 170.28112793 8.69215393 6.15908766 169.36802673 9.71847534
		 6.022060394 169.077270508 10.14103699 6.36130905 169.74223328 9.52952576 5.69970369 169.20831299 10.84251404
		 6.8911891 170.89889526 8.50605774 6.45614767 170.84521484 9.14831543 6.97024584 171.49450684 7.93910217
		 7.79961061 171.69351196 5.58644104 7.47281313 172.4099884 5.5612793 6.45406437 173.22132874 6.51734924
		 5.31608629 174.19779968 7.087036133 5.76387167 174.62423706 5.59741211 4.77155733 175.25965881 6.30438232
		 5.08391428 175.36170959 5.3807373 6.096805573 174.81614685 4.11886597 5.35203552 175.50082397 4.045776367
		 5.021139622 175.4316864 5.21707153 5.25794744 175.52651978 4.041671753 4.97402716 175.49778748 2.67648315
		 4.77258253 175.51437378 3.51242065 4.50709009 175.36769104 5.16323853 4.27877665 175.19555664 6.21385193
		 3.15274763 175.77693176 5.99542236 3.76033092 174.8789978 7.67527771 2.39287138 175.79075623 6.77909851
		 2.33828092 175.22216797 7.99092102 3.29311419 174.41355896 8.83540344 3.86956549 174.77624512 8.19966125
		 3.76433635 174.57284546 8.56199646 3.48265362 173.51570129 10.034393311 3.95061207 174.73680115 8.24821472
		 4.50443506 173.5769043 8.86280823 5.90877199 170.34025574 10.04045105 3.75175214 171.96789551 10.8421936
		 3.26327443 172.89230347 10.61531067 2.6623075 172.31588745 11.39541626 2.81235838 171.83250427 11.56488037
		 5.028018951 170.62515259 10.56352234 4.69144344 169.37332153 11.35723877 1.95966387 170.75921631 12.32693481
		 1.97495222 172.17886353 11.46473694 1.71338916 171.2769165 12.062469482 1.36921632 170.62559509 12.69424438
		 0.9625091 171.62414551 12.26799011 0.46728647 171.45783997 12.85884094 0.21551003 170.44920349 13.63249207
		 0.059593443 171.043884277 13.50668335 0.10906862 171.67800903 13.14746094 0.099987961 171.87973022 12.96286011
		 -0.057007685 171.7668457 13.13423157 -0.031635065 171.93701172 12.92674255 0.015331239 172.28788757 12.29092407
		 -0.32340637 172.037902832 12.44326782 -0.46482053 172.7361908 11.67707825 -0.51757282 173.64181519 10.72644043
		 -0.8999421 173.18882751 11.25965881 -0.89281976 174.68373108 9.59153748 -0.98296916 174.71096802 9.48681641
		 -1.13091528 173.78240967 10.39151001 -1.069912672 172.51213074 11.55778503 -2.15208364 172.72262573 11.022781372
		 -1.96014643 172.18057251 11.46200562 -0.93120718 171.57228088 12.30717468 -0.4214642 171.47523499 12.88153076
		 -0.81484574 168.92788696 13.58129883 -1.37872624 170.61689758 12.68496704;
	setAttr ".vt[1328:1493]" -1.70251298 171.28358459 12.053787231 -1.94003129 170.77258301 12.3196106
		 -1.96460915 169.9627533 12.68254089 -2.77078557 171.86521912 11.56599426 -2.64592528 172.33334351 11.38334656
		 -3.73033881 171.96707153 10.84492493 -4.99661016 170.6519928 10.56022644 -4.67098045 169.36909485 11.35949707
		 -5.67230463 169.18254089 10.85784912 -5.44800997 168.21755981 11.27786255 -5.3927269 167.82926941 10.77670288
		 -6.129282 169.29093933 9.90368652 -6.48035288 170.0055084229 9.25292969 -6.6306324 170.2170105 8.77639771
		 -6.098891735 169.57514954 8.99066162 -6.78843164 170.40318298 8.5193634 -6.74785089 170.33587646 7.73643494
		 -7.15279722 170.67707825 7.37290955 -7.22941446 170.83122253 7.42253113 -7.41004229 170.91035461 6.94068909
		 -6.87442923 170.89996338 8.50097656 -7.56336069 171.13850403 6.42466736 -7.78607273 171.69291687 5.57058716
		 -6.94894409 171.50057983 7.93515015 -6.442729 170.83442688 9.15142822 -5.89200783 170.33874512 10.039337158
		 -3.45996165 173.52941895 10.027770996 -3.25755382 172.90567017 10.59417725 -3.19614291 173.62644958 9.88970947
		 -3.2687614 174.41015625 8.84266663 -3.84208655 174.74169922 8.30639648 -3.9565208 174.73284912 8.22183228
		 -4.070999622 175.0035400391 7.36834717 -3.74907756 174.8687439 7.69274902 -4.25402498 175.18942261 6.24601746
		 -3.13645506 175.77488708 5.99769592 -4.48445177 175.36695862 5.1733551 -4.90068388 175.39082336 5.55915833
		 -4.50928307 175.27397156 6.37696838 -4.51223135 175.2102356 6.65664673 -4.76390982 175.23735046 6.32313538
		 -5.29859924 174.19580078 7.087295532 -4.48466063 173.57713318 8.8631897 -6.4360137 173.22247314 6.51309204
		 -5.7396884 174.62802124 5.60173035 -6.62795067 173.62678528 5.44570923 -7.45354557 172.40950012 5.56239319
		 -7.070611954 173.68336487 4.099731445 -7.81720066 172.55175781 4.017227173 -7.45495319 173.36531067 3.23387146
		 -7.71495724 172.9173584 2.66651917 -7.48576736 173.50619507 1.79325867 -6.72025824 174.54833984 1.61445618
		 -6.91664076 174.37042236 0.49508667 -7.57420063 173.33918762 0.20246887 -7.58155346 173.16268921 -1.1131134
		 -7.21006775 173.53469849 -1.72068787 -6.78785944 174.097854614 -1.27708435 -6.54366255 174.79037476 0.11221313
		 -6.098767757 175.02986145 -0.71769714 -5.92906809 175.29928589 -0.072402954 -5.93385935 175.36135864 0.67953491
		 -5.82597494 175.42976379 0.6681366 -5.66723871 175.47225952 1.41836548 -5.58043718 175.54766846 2.4747467
		 -5.46179342 175.56680298 2.52111816 -5.2723918 175.52867126 4.036895752 -5.3497262 175.46246338 4.14892578
		 -4.98175716 175.42938232 5.12522888 -5.046587467 175.35890198 5.44041443 -6.080830574 174.81336975 4.11766052
		 -4.95021677 175.49983215 2.68783569 -4.74669886 175.5184021 3.50741577 -2.59860849 176.42756653 4.22988892
		 -2.094798088 176.82681274 2.48274231 -1.52025163 176.96960449 3.27310181 -1.91819346 176.58450317 4.77676392
		 -0.90106124 177.054656982 3.9370575 -0.73512262 176.84860229 5.058166504 -2.37938929 175.78817749 6.78082275
		 -0.926265 176.20213318 6.74746704 -1.096160054 175.80757141 7.46788025 -0.90885854 175.68370056 7.95724487
		 -1.057253003 175.473526 8.063919067 -0.88563073 175.34458923 8.73075867 -0.79199994 175.42449951 8.67185974
		 -0.68141997 175.16607666 8.98529053 -0.39429784 175.50511169 8.27615356 -0.48245797 174.73202515 9.41253662
		 0.01071313 174.43559265 9.84414673 0.51163733 174.75706482 9.37811279 0.516846 173.57511902 10.80491638
		 0.90472579 174.83280945 9.41290283 0.87307447 173.12509155 11.32589722 1.017059565 173.68969727 10.64749146
		 0.97720683 173.11221313 11.26005554 0.81267142 172.54756165 11.65979004 1.05032742 172.48480225 11.59078979
		 1.16372681 173.62644958 10.54318237 3.22911429 173.6270752 9.88487244 1.1117872 174.69291687 9.29161072
		 1.0046042204 174.6953125 9.49533081 0.85938019 175.42764282 8.63017273 1.056890249 175.46958923 8.14147949
		 1.13798118 175.79693604 7.47572327 0.87324315 175.55357361 8.24263 0.9174298 176.18690491 6.80622864
		 0.51600665 175.63044739 8.10012817 0.75606483 175.27255249 8.85922241 0.013870211 176.51742554 6.19526672
		 -0.62274873 175.69406128 7.95600891 0.74494153 176.87153625 4.98931885 1.92997515 176.58808899 4.77197266
		 0.91271847 177.058868408 3.91973877 -0.0078434255 177.34765625 2.83956909 0.42273992 177.322052 2.36103821
		 1.53629601 176.970047 3.272995 2.11250734 176.82759094 2.48666382 1.018302917 177.098587036 1.33724976
		 2.0061860085 176.77215576 0.84069824 3.74461174 176.060501099 1.56257629 3.36963558 176.073471069 -0.12359619
		 4.99244642 175.43669128 1.36199951 5.44554234 175.35658264 1.061721802 5.48647833 175.56707764 2.54191589
		 5.71388578 175.43199158 1.019012451 5.5993495 175.54600525 2.49961853 5.90410471 175.40093994 0.81622314
		 6.7376833 174.5493927 1.61883545 6.56381416 174.78909302 0.11808777 6.93489552 174.37184143 0.49726868
		 7.50459766 173.50547791 1.80206299 7.47066832 173.36782837 3.2421875 7.73770189 172.91175842 2.6375885
		 7.83950758 172.54679871 4.013824463 8.051368713 172.52015686 2.1322937 8.37442398 171.84925842 2.25878906
		 8.10267067 171.76670837 4.36386108 8.15645218 171.37483215 4.15281677 7.96130419 171.29550171 5.23643494
		 7.95153093 171.19973755 5.18435669 8.11631584 171.24543762 3.97325134 8.17686081 171.22689819 3.52087402
		 8.37545395 171.31987 2.47831726 7.88365459 170.91127014 2.72183228 7.88742447 170.88269043 3.47279358
		 7.80262136 171.015899658 4.34434509 7.78852749 170.81311035 4.50260925 8.10800743 170.66545105 3.95623779
		 7.89280653 170.34953308 5.27708435 7.23749304 170.60317993 6.53044128 7.22637892 170.65786743 6.53924561
		 8.33410072 169.44390869 4.50733948 8.091821671 169.25918579 5.38430786 8.46190834 169.43199158 3.97077942
		 8.48770714 170.30583191 3.35771179 8.38358879 170.60351563 2.786026 8.2991581 170.58000183 2.50926208
		 8.45888138 170.43959045 2.53939819 8.46691704 170.4594574 2.025558472 8.63086319 170.49858093 1.016067505
		 8.44810867 170.57298279 1.27030945 7.90796614 170.82756042 1.65931702 8.12774467 170.55543518 2.095092773
		 7.8966651 170.90008545 1.68263245 8.0788517 170.85888672 1.36068726;
	setAttr ".vt[1494:1659]" 8.37924576 170.80664063 0.95578003 8.53872299 171.12312317 1.077590942
		 8.41080475 171.085586548 1.27713013 8.38217735 171.14625549 1.76052856 8.54687119 171.7936554 -0.30422974
		 8.5347538 171.58728027 -1.037063599 8.51497269 170.68534851 0.18624878 8.30306625 170.40115356 -1.0043334961
		 8.051986694 172.03237915 -2.11264038 8.0047092438 172.40348816 -1.48164368 7.23042345 173.53276062 -1.72201538
		 7.60791302 173.15246582 -1.11587524 7.5927043 173.34135437 0.20527649 7.75897169 172.79972839 0.54441833
		 8.18481255 172.3626709 0.075271606 6.81051922 174.096557617 -1.2698822 6.96195984 172.88017273 -3.53994751
		 6.34851551 173.99320984 -2.17607117 6.11900806 175.032180786 -0.71180725 5.96597767 175.27909851 -0.14831543
		 5.069336414 175.24153137 -0.16567993 5.72817945 175.25292969 -0.034500122 5.78246832 175.45254517 0.9140625
		 5.43357992 175.17747498 0.10147095 5.15579557 174.86709595 -1.67585754 5.30661011 174.47306824 -2.51210022
		 4.39647055 174.77130127 -3.13475037 5.90806532 173.36491394 -3.75007629 4.29975748 174.10414124 -4.31004333
		 3.36094594 174.97627258 -3.6803894 3.25746202 174.32733154 -4.80374146 2.33766389 174.87940979 -4.55787659
		 2.28699422 173.99989319 -5.81626892 3.85699463 173.61657715 -5.33413696 2.96815062 173.30671692 -6.23129272
		 2.16287541 172.95054626 -6.92579651 1.17325592 173.72634888 -6.48712158 1.14500153 174.67822266 -5.337677
		 0.51824474 174.04498291 -6.53253174 0.0071430649 173.91931152 -6.83378601 0.0042523956 172.58766174 -7.97627258
		 -0.49703583 174.053482056 -6.52284241 -1.15316617 173.72459412 -6.48995972 -1.13066661 174.66938782 -5.34783936
		 -0.65614963 174.96733093 -5.40872192 -0.2013526 175.49946594 -5.36660767 0.0094431806 174.90345764 -6.062683105
		 -0.069081187 175.60256958 -5.34335327 0.11804705 175.68528748 -5.26594543 0.6715858 174.97761536 -5.40249634
		 0.64224344 175.91183472 -3.9447937 0.15114151 176.19662476 -4.41366577 0.0031911025 175.91087341 -4.92852783
		 -0.14602055 176.17729187 -4.42962646 -0.034259468 176.56523132 -3.38645935 -0.28008571 176.72984314 -2.51081848
		 -0.62284648 175.90657043 -3.95837402 -0.69215262 176.5178833 -2.10508728 -1.12591541 175.9394989 -3.082290649
		 -1.091786265 176.47807312 -1.59355164 -1.86316764 176.22151184 -1.86009216 -0.98228997 176.87373352 -0.21339417
		 -2.13392711 176.40736389 -0.87437439 -2.88731146 175.75228882 -2.2540741 -3.78642607 175.55325317 -1.7051239
		 -3.34796572 176.074829102 -0.12242126 -5.0555439 175.23497009 -0.19070435 -4.98001671 175.4335022 1.36181641
		 -5.41205645 175.17848206 0.090621948 -5.43349457 175.35359192 1.040252686 -3.73207998 176.057357788 1.56011963
		 -1.98901379 176.77085876 0.83625793 -0.99962968 177.098342896 1.33334351 -0.32887715 177.35092163 2.31852722
		 -0.17792934 177.47380066 1.0061950684 0.23215699 177.47509766 1.18264771 0.025122235 177.30171204 -0.58015442
		 -0.30082256 177.20817566 -0.60820007 0.30315048 177.21206665 -0.63700867 1.0046530962 176.87257385 -0.21295166
		 0.70422733 176.51678467 -2.11889648 1.11818576 176.48097229 -1.57754517 1.88308418 176.22200012 -1.85848999
		 2.15567279 176.40719604 -0.87069702 2.9161396 175.74946594 -2.25221252 2.16521978 175.61158752 -3.25212097
		 1.14560091 175.93403625 -3.09475708 1.14348733 175.39016724 -4.23806763 0.30478016 176.7277832 -2.50819397
		 3.80915332 175.55212402 -1.70330811 0.16701159 176.68829346 -2.85133362 -5.13756275 174.8653717 -1.67816162
		 -5.28923893 174.46850586 -2.51556396 -4.37839699 174.77279663 -3.13061523 -5.076471329 173.48130798 -4.12921143
		 -6.49927616 173.16708374 -2.80969238 -6.29076719 174.0019836426 -2.20419312 -5.6439662 171.96923828 -4.9427948
		 -7.17814112 170.96916199 -4.16082764 -6.42415285 171.13967896 -4.82754517 -4.1066432 172.45863342 -6.32824707
		 -3.26393485 172.070831299 -7.17176819 -2.95144868 173.30656433 -6.23023987 -2.13871789 172.95109558 -6.92683411
		 -2.27091837 174.00076293945 -5.81388855 -3.83207345 173.62359619 -5.32873535 -3.23622632 174.33277893 -4.79727173
		 -4.27672434 174.1053009 -4.31002808 -3.33954167 174.9776001 -3.67927551 -2.14832735 175.61134338 -3.25119019
		 -2.31730294 174.8800354 -4.55677795 -1.12699878 175.38079834 -4.25622559 -8.027429581 172.040863037 -2.10661316
		 -7.97685814 172.42266846 -1.46612549 -8.51585197 171.59092712 -1.037216187 -7.98445463 170.89364624 -3.2225647
		 -8.022403717 170.37110901 -2.17411804 -8.49209404 170.67463684 0.1723938 -8.29198837 170.41160583 -0.96846008
		 -8.15812492 169.90339661 -1.90065002 -8.61037064 170.018310547 -1.12649536 -8.70831108 170.45817566 0.1946106
		 -8.8307209 169.89659119 -0.28335571 -8.74181747 169.54098511 -1.19134521 -8.84400368 169.4183197 1.13302612
		 -8.58258438 169.18287659 0.29434204 -8.53136063 169.10125732 1.37702942 -8.63389969 169.43078613 3.014907837
		 -8.65373421 169.53056335 3.22679138 -8.29669762 169.40544128 4.58773804 -8.28607941 169.34106445 4.40959167
		 -7.71667528 169.018035889 6.4414978 -7.80354548 169.19372559 6.36087036 -7.50230742 168.83900452 7.0058898926
		 -7.50231791 168.88249207 7.31628418 -7.57293177 169.071258545 7.17909241 -7.025803089 168.37838745 8.48129272
		 -6.8375783 168.58328247 8.84092712 -6.95543146 168.19337463 8.63548279 -6.32130146 166.82981873 9.6245575
		 -6.31136131 166.5776062 9.40489197 -5.84470415 167.4112854 10.016311646 -6.85639477 168.19273376 8.091247559
		 -6.93028498 168.21157837 8.35704041 -7.1134305 168.38421631 8.17785645 -6.66712618 168.95812988 8.90167236
		 -6.38123178 169.079574585 8.96626282 -6.10717535 169.54260254 8.9548645 -5.74912405 168.62705994 9.68315125
		 -6.81128645 170.29684448 7.39801025 -6.8353982 169.91696167 7.82574463 -6.83485174 169.53637695 8.099395752
		 -7.094661236 169.87454224 7.49943542 -6.99201822 169.34634399 8.13661194 -7.90086603 169.44429016 6.10383606
		 -7.16666269 170.63026428 6.60647583 -7.35074472 170.76728821 6.21379089 -7.56405401 170.97697449 6.30102539
		 -7.82376909 171.13591003 5.64485168 -7.78205824 171.020858765 4.37554932 -8.20445442 171.27961731 3.50271606
		 -8.23656082 171.35997009 3.46762085 -8.36472702 171.31214905 2.38319397 -8.3530674 171.86036682 2.24378967
		 -8.52092552 171.10704041 1.056442261 -8.06457901 171.13871765 2.16711426;
	setAttr ".vt[1660:1825]" -7.86496782 170.86427307 1.60145569 -7.88323545 170.93196106 2.6750946
		 -7.89298868 170.88252258 2.69953918 -7.89488268 170.85688782 3.473526 -7.92622328 170.9831543 3.62496948
		 -7.82621813 170.88676453 3.81245422 -7.77923441 170.76980591 4.55220032 -8.13255692 170.64788818 3.86532593
		 -7.39560652 170.72271729 5.7792511 -7.87038469 170.338974 5.29269409 -8.47525024 170.29437256 3.34448242
		 -8.35698509 170.60702515 2.75827026 -8.098480225 170.56193542 2.12721252 -8.30859566 170.50947571 2.18174744
		 -8.46849442 170.38424683 2.18659973 -8.49596596 170.4624939 1.73703003 -8.72178459 169.76512146 2.30525208
		 -8.62554169 169.76077271 3.45256042 -8.84017944 169.87963867 1.19007874 -8.59540939 170.52146912 1.073791504
		 -8.38093185 170.75978088 0.92546082 -8.52883148 171.79089355 -0.32290649 -8.044330597 172.50370789 2.10047913
		 -8.088199615 171.76142883 4.3556366 -8.16559982 172.36399841 0.11231995 -7.74381828 172.78549194 0.49217224
		 -7.9579525 171.3061676 5.19515991 -7.8825717 168.86602783 4.57574463 -8.29611778 168.84072876 2.37619019
		 -8.28589249 169.21539307 3.29559326 -8.43889618 168.75856018 0.99382019 -8.44853783 168.98490906 -0.84732056
		 -8.45057487 169.23106384 -1.47210693 -8.23032379 169.37362671 -1.99835205 3.28475714 172.073440552 -7.17034912
		 4.11536455 172.45770264 -6.33682251 8.042470932 171.11625671 2.099395752 7.363832 170.8614502 6.99226379
		 7.43132639 170.97642517 6.92315674 6.67825317 170.35321045 8.90989685 7.092494965 173.68031311 4.098175049
		 6.65027332 173.62413025 5.44419861 2.61225486 176.42976379 4.23117065 2.24675941 172.75683594 10.97509766
		 0.36211947 172.054473877 12.41870117 0.47685108 172.74728394 11.65975952 -1.098797679 174.75489807 9.19618225
		 -2.31918573 175.22175598 7.99156189 -2.49408054 168.37796021 13.029891968 -1.5161618 168.48847961 13.55221558
		 -1.26201403 168.28642273 13.47825623 -0.92682427 168.47444153 13.46755981 -0.11425349 170.24134827 13.82165527
		 -0.099373646 169.25294495 14.30152893 0.055623677 170.26541138 13.82823181 4.29526854 175.10012817 7.076034546
		 4.5030179 175.25630188 6.47824097 7.21274662 168.51164246 7.45251465 6.87734365 168.19230652 8.089675903
		 7.16305399 168.15487671 7.12980652 7.44518089 166.28781128 7.54458618 7.38782358 165.91885376 7.016662598
		 4.86062813 168.71891785 -7.88731384 4.11168385 168.54838562 -8.28581238 4.59282589 167.5491333 -8.12585449
		 5.55460405 165.54559326 -7.6031189 2.34401798 170.13665771 -9.037689209 1.96465051 170.74954224 -8.86711121
		 0.0018237429 164.022567749 -9.058731079 -0.74588579 164.19232178 -8.98538208 -0.78125805 161.33226013 -8.81471252
		 -0.055266712 161.6519928 -8.95684814 -0.34555933 160.97305298 -8.81602478 -0.032709319 161.13442993 -8.79866028
		 -3.27933431 167.77380371 -8.72268677 -3.79647875 165.80448914 -8.33889771 -4.456357 167.35253906 -8.10717773
		 -5.65714931 167.4928894 -7.46434021 -6.95813513 167.033157349 -7.82795715 -5.87362909 166.99209595 -8.55870056
		 -5.41691828 165.80274963 -8.88088989 -5.16763306 167.10696411 -8.94343567 -4.42229462 166.98402405 -9.23930359
		 -3.73437095 167.93582153 -9.46511841 -2.61467361 167.51631165 -9.85430908 -3.63928795 165.55883789 -9.45724487
		 -2.41111994 165.41647339 -9.75094604 -4.066150188 162.93482971 -9.28997803 -4.64631367 165.64143372 -9.10572815
		 -4.4724226 162.91371155 -9.15042114 -4.4486351 162.28031921 -9.10084534 -4.91095877 164.69093323 -8.95240784
		 -5.17661142 163.85714722 -8.69009399 -2.46631908 168.69526672 -9.82568359 -2.64238644 169.59848022 -9.58486938
		 -1.60319424 171.034561157 -9.31526184 -2.88652086 171.53491211 -8.7039032 -2.037955999 171.99308777 -8.66371155
		 -3.15361238 172.54527283 -7.96495056 -8.36523056 170.29370117 -4.79135132 -6.8676362 171.53987122 -5.51130676
		 -6.93735504 172.049163818 -4.76431274 -6.56771612 170.59526062 -6.66488647 -5.84390974 174.29052734 -3.95925903
		 0.90432167 176.53401184 -4.33764648 0.48074526 177.36138916 -3.46182251 0.94805533 177.24971008 -2.54660034
		 1.15739024 177.65045166 -0.12693787 1.26448882 177.40719604 -0.82649231 1.25584781 177.61418152 0.037719727
		 1.52199793 177.32601929 -1.23582458 1.477265 177.68151855 0.52798462 2.47835827 177.4047699 0.38015747
		 2.55991554 177.51091003 1.98245239 4.28753328 176.68592834 1.21495056 4.36189699 176.65689087 2.43855286
		 5.15277195 176.18786621 -0.10671997 6.13214731 175.48249817 0.9901123 6.17416668 175.44309998 -0.39155579
		 5.25284576 176.0099945068 -1.053009033 2.65525603 177.043746948 -1.14558411 5.014475346 175.90962219 -1.92222595
		 2.78499174 176.62200928 -2.49183655 1.56447494 176.62536621 -3.34649658 3.68502569 175.7696991 -3.88420105
		 2.98655581 175.51564026 -4.85426331 4.24768496 175.41108704 -3.99557495 4.37616014 175.80282593 -3.11184692
		 5.80324507 174.93655396 -3.058624268 5.95566702 175.26322937 -1.97973633 7.068339348 174.2723999 -1.98735046
		 7.28500986 174.49353027 -0.32006836 7.68131733 173.46574402 -1.89346313 8.72098923 172.11032104 -1.1774292
		 8.38260651 172.85661316 -0.19769287 8.091444016 173.36357117 0.8908844 7.29636383 174.41705322 1.39611816
		 6.27258873 175.1381073 3.35021973 4.77058458 176.30784607 3.48066711 5.27830267 175.67536926 4.70838928
		 6.20132446 174.7664032 5.082794189 7.15140629 174.23620605 3.615448 6.94041491 173.91410828 5.18112183
		 5.92074728 174.43148804 6.35662842 6.77842855 173.13697815 6.79515076 6.1759963 173.38716125 7.4468689
		 7.38182449 171.75447083 7.6058197 7.77334976 172.54846191 5.59031677 8.26699257 171.8299408 5.094787598
		 7.15731239 171.12980652 8.50152588 8.16409874 171.29827881 5.34156799 8.46797371 171.44439697 3.9914093
		 8.10411644 171.15480042 4.55744934 7.94983912 171.099182129 5.2762146 7.33594608 170.82810974 7.7596283
		 7.49492693 170.82424927 6.73583984 7.14577198 170.53956604 7.59716797 7.35202074 170.6401062 7.067230225
		 7.71102905 170.82939148 5.95314026 7.55144882 170.21537781 7.15100098 7.94134045 169.56950378 7.0064849854
		 8.11293602 170.60314941 5.36779785 7.90359211 170.81239319 5.43003845 8.098100662 170.95471191 4.49330139
		 7.88218927 170.98841858 5.30131531 8.21694756 171.10096741 3.69711304;
	setAttr ".vt[1826:1991]" 8.33161736 170.94804382 3.41676331 8.3045845 171.16654968 3.49436951
		 8.31573868 171.065261841 2.88546753 8.35193825 170.96255493 2.85855103 8.20520401 170.98847961 2.11813354
		 8.33953094 171.13792419 1.97203064 8.42285919 171.11955261 1.74528503 8.77419853 171.24417114 1.6749115
		 8.62532616 171.30215454 2.60598755 8.82852364 171.61947632 1.90136719 8.92543602 171.0055084229 1.13539124
		 9.07172966 171.63243103 -0.13183594 9.093305588 170.83422852 -0.085418701 8.98904991 170.67863464 1.13395691
		 8.69028473 170.89775085 1.31227112 8.44828033 170.91616821 1.59690857 8.61975288 170.76805115 1.44544983
		 8.45553207 170.77435303 1.7077179 8.9228344 170.662323 1.30618286 8.54192924 170.64294434 1.76034546
		 8.86707497 170.53903198 1.85105896 9.16186523 169.85595703 2.18847656 8.74438286 170.6993103 2.8092804
		 9.052520752 169.69830322 3.24824524 9.44059944 169.29846191 1.22930908 8.87799454 169.41737366 3.832901
		 8.15502167 169.014953613 6.78862 8.4509716 169.058486938 4.29212952 7.79715109 168.5513916 6.97006226
		 7.49571276 168.35752869 8.34187317 7.47031784 168.41653442 8.42608643 6.89577579 166.91401672 9.82052612
		 7.023167133 167.32991028 8.96017456 7.50126314 168.24261475 7.85035706 7.27917528 167.75119019 8.33483887
		 7.47498035 167.91026306 7.86346436 7.36732244 167.5423584 8.32992554 7.81926394 168.28245544 6.97999573
		 7.78870964 168.4103241 6.91200256 8.099481583 168.68836975 5.53175354 8.40019608 168.84643555 4.31118774
		 8.43841553 168.5925293 4.56326294 9.040708542 168.10069275 2.94624329 8.88606262 168.61395264 2.26622009
		 8.56072235 168.89497375 3.55412292 8.94234467 168.82830811 1.93476868 9.096494675 168.45439148 0.13182068
		 9.30467033 167.97001648 1.36686707 9.40226555 167.85688782 0.14138794 9.57261848 165.51750183 0.37716675
		 9.38393593 165.48814392 2.055618286 9.84268951 163.94926453 1.23535156 9.43377495 164.48478699 3.69352722
		 9.91760826 162.8339386 3.66711426 10.027984619 163.047149658 1.84893799 10.015205383 162.92956543 1.76266479
		 10.084394455 162.95265198 1.51829529 9.48745537 162.88290405 0.46589661 10.029191971 163.057952881 0.62026978
		 9.26502609 163.23750305 -0.014251709 9.14469147 163.5307312 -0.68560791 9.34150314 162.95347595 1.021820068
		 9.15032578 162.74249268 3.80299377 9.54881287 162.57809448 5.99707031 9.59045219 162.73815918 6.55854797
		 8.944561 162.53033447 6.2227478 8.85218239 163.071884155 7.098831177 8.85517502 163.22918701 7.16703796
		 8.79758644 163.11051941 7.23712158 8.34502792 164.31144714 7.69511414 8.31592178 163.42970276 8.39627075
		 8.15962219 163.51228333 8.77966309 8.072629929 163.21226501 9.037780762 7.65827227 163.21437073 9.94317627
		 7.98355103 163.87757874 8.71662903 8.19685173 164.1776123 8.077301025 8.10964584 164.23669434 8.2313385
		 7.97528267 164.68696594 7.75244141 8.49697113 164.33439636 7.52502441 8.10757637 164.96487427 7.70458984
		 7.9435029 164.800354 7.83010864 8.13245964 165.31382751 7.93890381 8.27428246 165.3318634 7.88543701
		 8.56926918 165.30656433 7.88336182 8.18754387 165.66163635 7.67425537 8.10411263 165.66000366 7.77284241
		 8.17206001 165.88638306 7.76928711 8.46920967 165.89494324 7.57078552 8.41879654 166.1086731 7.5708313
		 8.54389763 165.65141296 7.550354 8.081884384 167.73297119 7.331604 8.88518333 165.62110901 6.34022522
		 8.30454826 167.9959259 6.260849 8.64143944 167.52516174 5.23524475 9.045175552 166.42811584 4.12748718
		 9.19758034 164.94548035 5.10800171 8.9718647 164.022201538 7.40405273 8.3392601 166.19526672 7.70251465
		 7.69685078 166.6199646 8.90368652 8.17633629 165.96160889 8.45785522 7.52041483 166.20979309 9.40919495
		 7.5613246 165.81921387 9.3195343 7.85142612 165.65364075 8.42581177 7.49965143 165.59106445 8.71255493
		 7.52640057 165.46641541 8.60671997 7.82548094 165.5252533 8.43437195 8.049024582 165.20202637 8.11837769
		 7.92334747 164.65222168 8.85908508 8.05768013 164.23680115 8.74891663 7.59006262 163.88293457 9.75817871
		 7.51636505 164.094314575 9.67088318 7.14420462 164.39649963 9.29931641 6.76111555 164.079528809 10.30630493
		 6.54631472 163.9803009 10.42980957 5.97744322 163.71717834 11.4415741 5.86418152 163.61112976 11.96203613
		 7.12001753 163.78965759 10.67228699 6.33498621 163.13989258 12.48066711 7.14136267 163.51751709 10.87846375
		 7.40994596 163.59822083 10.22631836 7.14758778 162.97372437 10.42192078 7.44245005 163.46813965 10.1530304
		 7.1206212 162.85906982 11.1698761 5.80200672 163.32997131 12.54963684 5.70183039 163.47010803 12.079620361
		 5.49280214 163.17192078 12.4879303 5.51231337 163.0075836182 12.64398193 6.05361414 162.92689514 12.8258667
		 5.53295708 162.91694641 12.77198792 5.76205158 162.82733154 13.046890259 5.39480639 163.03263855 13.57165527
		 7.41779232 164.83062744 8.6918335 7.59008074 165.28198242 8.57168579 7.010036945 165.83485413 9.20625305
		 6.76551628 166.17340088 9.90847778 7.097402096 166.21261597 9.74131775 5.87476301 166.81367493 11.46575928
		 6.25270081 166.29289246 10.084732056 5.77066612 166.5408783 10.65397644 5.27719307 166.74530029 11.58230591
		 5.83543396 167.005279541 11.66690063 6.28575945 169.078979492 9.82891846 6.41629028 169.46897888 9.43757629
		 6.49935722 169.32290649 9.39021301 7.008225441 169.36244202 8.99533081 6.66111279 169.45913696 9.10791016
		 7.083974361 169.75152588 8.47930908 6.92549562 170.10664368 8.17500305 6.83963585 170.21630859 8.21353149
		 7.16977692 170.33589172 7.57286072 6.78032923 170.20652771 8.40156555 6.57223368 169.60316467 9.026626587
		 6.81166124 170.25054932 9.07989502 6.6967783 170.28915405 9.51876831 6.26001835 168.95144653 10.29754639
		 6.24611568 169.35639954 10.49516296 6.0090055466 169.5983429 10.91960144 5.81967068 168.25119019 11.48413086
		 6.39576674 170.79705811 9.72921753 6.89555359 171.57815552 8.50944519 4.42600393 174.16249084 8.76748657
		 4.7524457 174.84819031 7.51506042 3.12032819 175.85713196 7.99163818 3.76945138 175.99433899 6.94966125
		 3.89840126 176.37767029 5.83459473 5.42248297 175.15594482 5.90473938;
	setAttr ".vt[1992:2157]" 4.33713293 176.34628296 4.83920288 3.66080308 176.84333801 4.42443848
		 7.35914326 170.13894653 7.58885193 7.25761271 169.89076233 8.16799927 7.22524643 169.60392761 8.41622925
		 8.31906128 169.80340576 5.7795105 6.40843534 167.86888123 10.34991455 6.4159441 166.75050354 10.78918457
		 6.89164209 166.38021851 10.10797119 6.83313036 166.85939026 9.41261292 6.93615294 166.48225403 9.63505554
		 6.92685032 166.65270996 9.29371643 6.90137529 166.93241882 9.18237305 7.077127457 166.76463318 9.11605835
		 7.16148663 167.34866333 8.63075256 7.15256119 166.37464905 9.47038269 9.16256714 168.71199036 -0.16928101
		 9.021509171 168.94073486 1.74891663 9.47631836 169.12168884 0.061096191 9.21074677 169.96903992 -1.043014526
		 9.090419769 171.41522217 -0.94065857 8.92972565 171.21426392 -2.095870972 8.60687447 171.98806763 -1.88026428
		 8.6694622 170.92015076 -3.23258972 8.38433075 170.29618835 -4.79232788 8.12407303 171.049957275 -4.33061218
		 6.97581863 172.6374054 -4.58233643 7.059156418 173.52789307 -3.39614868 7.87920475 172.063247681 -3.52125549
		 8.24577141 171.47241211 -3.25715637 5.86220932 174.29078674 -3.95974731 5.48260212 172.80023193 -6.0809021
		 6.45548105 172.095489502 -5.74008179 5.51538563 172.18074036 -6.6468811 4.71152735 172.34825134 -7.22436523
		 4.59594297 173.58729553 -6.02142334 3.57821584 173.31295776 -7.081329346 3.32013845 174.81176758 -5.63926697
		 1.49436963 175.91571045 -4.81196594 3.16705489 172.55410767 -7.96138 4.68157625 171.46105957 -7.93911743
		 4.98578978 171.72032166 -7.51164246 6.92293358 169.0834198 -7.25900269 6.53521347 170.99343872 -6.49655151
		 7.20323467 171.52470398 -5.32922363 8.51939011 170.7504425 4.0074310303 8.30060959 170.86228943 2.49661255
		 8.61024475 172.1199646 2.84385681 8.18664742 172.78952026 3.72946167 8.4991188 172.51109314 2.21716309
		 7.96421671 173.43130493 2.3152771 7.71867943 173.27807617 4.326828 4.53363514 162.26142883 -8.63389587
		 9.25274467 163.46350098 -1.11737061 9.093105316 163.40893555 -1.088348389 4.25866699 162.10983276 -8.12794495
		 3.35250497 162.042037964 -8.40319824 -6.7281661 166.085266113 -7.30412292 -2.55721426 162.182724 -8.58782959
		 -2.43760276 162.66390991 -8.72943115 5.88187647 164.082260132 -7.5327301 7.093437195 167.16645813 -6.79638672
		 8.470541 162.65008545 -3.91360474 8.42471123 163.97930908 -3.61061096 8.82104111 164.11605835 -2.14825439
		 8.56082344 166.21636963 -1.56526184 8.7050705 165.66926575 -1.10035706 8.98551559 163.91065979 -1.41165161
		 9.044563293 163.16593933 -1.55685425 9.032814026 162.73953247 -1.97512817 9.093105316 163.40893555 -1.088348389
		 9.14469147 163.5307312 -0.68560791 9.26502609 163.23750305 -0.014251709 9.34150314 162.95347595 1.021820068
		 9.046583176 163.97012329 1.22070313 8.5283947 162.92881775 7.76702881 8.79758644 163.11051941 7.23712158
		 5.27719307 166.74530029 11.58230591 0.02898577 165.7676239 14.096237183 -0.78231508 164.2303772 14.80172729
		 -0.80120021 164.099029541 14.83821106 -7.47634649 165.58763123 8.70625305 -7.56310129 165.25872803 8.58428955
		 -6.42227888 163.83656311 10.42579651 -6.55130863 164.015533447 10.56504822 -5.97768164 163.72239685 11.39054871
		 -5.97892475 163.64274597 11.31225586 -5.58262157 163.35842896 12.16894531 -5.59220839 163.14678955 12.12054443
		 -5.32085419 163.0089874268 12.4957428 -5.3765769 163.069946289 12.59884644 -4.92829418 163.21076965 12.89149475
		 -5.48990536 161.87515259 12.70350647 -4.067486763 161.97914124 14.0070495605 -4.77985048 161.92558289 13.36555481
		 -4.69464779 161.80656433 13.59420776 -4.006919384 161.77070618 14.21183777 -4.028135777 161.7195282 14.31088257
		 -3.077823162 161.47540283 14.91419983 -3.81575489 161.70620728 14.91362 -3.14497089 161.43759155 15.26023865
		 -3.16654253 161.48419189 15.3183136 -3.93412733 162.53813171 14.73358154 -2.8579731 162.20115662 15.32475281
		 -3.22889948 162.50241089 15.052154541 -2.39112926 162.3454895 15.42124939 -3.28414297 163.031341553 15.05305481
		 -1.96361423 162.34298706 15.60800171 -2.41364217 163.1065979 15.37380981 -3.15612984 163.46089172 14.7195282
		 -2.35780382 163.41845703 15.014572144 -2.27300072 163.42521667 14.75180054 -3.4838686 163.41873169 14.46554565
		 -3.77583981 163.31079102 14.35827637 -3.90138388 163.30891418 14.069534302 -3.59184647 163.29144287 14.15382385
		 -3.75404596 163.18925476 13.98474121 -4.1223793 163.28578186 13.78097534 -4.30832672 163.25013733 13.89259338
		 -5.2526536 163.2684021 13.028396606 -4.92829418 163.21076965 12.89149475 -5.3765769 163.069946289 12.59884644
		 -5.37515593 163.031494141 13.57359314 -5.5345273 162.91389465 12.77146912 -5.54853249 162.97888184 12.64460754
		 -5.77268505 163.34043884 12.54197693 -6.0078673363 162.8677063 12.87646484 -6.32518673 163.14282227 12.46533203
		 -6.17960072 161.89373779 12.93882751 -5.6735568 162.38804626 13.37312317 -5.13789082 162.17552185 13.93617249
		 -5.011240959 161.90487671 14.015716553 -4.88892078 161.84155273 14.018432617 -5.54958916 161.77827454 12.8717041
		 -6.21597004 161.5004425 11.97216797 -6.81345367 161.63813782 12.11314392 -6.43043804 161.4618988 11.56446838
		 -6.37207317 161.53204346 11.55062866 -6.77404261 161.83215332 10.71125793 -7.14205599 161.77711487 11.20120239
		 -7.36364794 162.050582886 10.58424377 -7.31893301 162.043395996 10.8740387 -7.32969904 162.34042358 10.95191956
		 -7.68708181 162.39302063 10.076644897 -7.52492666 162.56526184 10.36315918 -7.63162756 163.22103882 9.95550537
		 -7.13067007 162.98161316 10.40081787 -7.40691614 163.49960327 10.17002869 -7.31094313 163.66595459 10.43902588
		 -6.99095678 163.67576599 10.98695374 -7.48386812 164.10089111 9.66992188 -6.55130863 164.015533447 10.56504822
		 -5.85319424 163.64547729 11.88392639 -5.97768164 163.72239685 11.39054871 -5.58262157 163.35842896 12.16894531
		 -7.12091684 163.41308594 10.90267944 -7.080740452 162.9455719 11.16940308 -7.12167406 164.40065002 9.27674866
		 -7.40365458 164.83108521 8.68557739 -7.56310129 165.25872803 8.58428955 -5.2532177 162.63078308 13.77386475
		 -4.39107847 162.89181519 14.43238831 -5.72671747 162.8392334 13.078018188 -3.56956434 163.052841187 14.10185242
		 -2.63540578 163.20019531 14.50701904 -1.51327538 163.22792053 14.99911499;
	setAttr ".vt[2158:2323]" -1.84705758 162.91978455 15.53581238 -2.96821547 161.65596008 14.76274109
		 -3.56956434 163.052841187 14.10185242 -2.63540578 163.20019531 14.50701904 -7.51305342 165.44184875 8.59465027
		 -7.47634649 165.58763123 8.70625305 -6.95513582 165.85505676 9.25431824 -6.16646385 166.3449707 10.22674561
		 -5.74919081 166.53486633 10.65301514 -5.31084538 166.72973633 11.53970337 -5.016218662 167.16876221 12.57569885
		 -4.51199532 167.062683105 12.30706787 -3.52827287 167.39752197 13.415802 -4.97026491 167.56292725 12.62994385
		 -5.31608486 167.59515381 12.33261108 -5.28700018 168.50785828 12.019088745 -5.82675171 168.27250671 11.44421387
		 -6.21299076 169.33370972 10.53320313 -5.96175385 169.55497742 10.97434998 -7.13374281 171.13090515 8.51187134
		 -6.37930202 170.79985046 9.72503662 -6.87725401 171.58093262 8.50585938 -7.36379719 171.75700378 7.60250854
		 -6.15507698 173.39070129 7.44555664 -6.75809097 173.140625 6.79174805 -5.90299845 174.42990112 6.35676575
		 -6.92023516 173.91514587 5.18247986 -7.75498581 172.54534912 5.59324646 -7.69933605 173.2779541 4.32923889
		 -8.16811943 172.78926086 3.72840881 -7.13036251 174.23843384 3.61317444 -7.94478035 173.42955017 2.33119202
		 -8.47876549 172.51307678 2.21617126 -8.58993149 172.11914063 2.85083008 -8.24749756 171.82888794 5.097015381
		 -8.35961342 172.86366272 -0.19470215 -8.073028564 173.36230469 0.89335632 -7.27666569 174.41833496 1.39076233
		 -6.25190926 175.13925171 3.35150146 -6.19015598 174.7613678 5.075698853 -5.26493168 175.67181396 4.70454407
		 -4.74930096 176.30961609 3.48014832 -4.32317114 176.33992004 4.85624695 -3.87729073 176.37789917 5.83804321
		 -5.41194534 175.1522522 5.89704895 -3.75001907 175.99559021 6.94851685 -2.76324153 176.52134705 6.9675293
		 -2.81633568 177.00028991699 5.4216156 -3.64132643 176.8447876 4.41772461 -3.10008335 175.85496521 7.99633789
		 -2.49589252 175.7169342 8.74565125 -1.70031512 175.67953491 9.11843872 -2.12837172 174.96405029 9.96026611
		 -2.93473077 175.30970764 8.93978882 -2.88767076 174.36645508 9.97898865 -4.40785456 174.16294861 8.76600647
		 -4.73317337 174.84967041 7.51329041 -3.88727689 173.58607483 9.86108398 -4.50048637 172.787323 9.99029541
		 -3.77695441 172.90672302 10.52125549 -2.75282407 173.20700073 11.045471191 -3.67180514 172.036804199 11.26522827
		 -2.039105892 172.63642883 11.8777771 -3.70952678 170.2644043 12.25952148 -4.65820074 170.24755859 11.62564087
		 -4.42410231 171.76078796 10.8553009 -2.46611476 169.42871094 13.23834229 -2.92543221 167.91169739 13.5933075
		 -1.55358994 168.58149719 13.92529297 -1.32907784 167.15757751 14.41642761 -2.75682926 167.15437317 13.82351685
		 -1.91322887 166.85897827 14.21166992 -1.81521094 166.50706482 14.18443298 -1.22668612 165.61245728 15.069839478
		 -1.017706513 166.41766357 14.93667603 -0.86873013 165.75596619 15.11756897 -0.44867501 165.58810425 15.40013123
		 -0.11388489 165.61262512 15.20436096 -0.47091267 166.0034790039 14.75971985 -0.6619308 166.0083312988 14.80465698
		 -0.51623607 166.23622131 14.66905212 -0.70042479 166.2381897 14.62754822 -1.065454364 166.94081116 14.27340698
		 -0.95445263 166.95137024 14.2472229 -1.32736385 168.50050354 13.82609558 -1.15500438 168.87016296 13.85865784
		 -0.99272031 168.50930786 13.862854 -0.88251776 168.86634827 13.92214966 -0.80855799 166.83621216 14.36909485
		 -0.64518154 167.080764771 14.55740356 -0.11230848 166.088088989 15.1960907 -0.085057586 165.7613678 15.18464661
		 0.093815945 165.97538757 15.27401733 0.0053316522 166.28773499 15.14021301 0.21510161 166.41195679 15.052536011
		 0.17713162 165.71424866 15.168396 0.4719713 166.11355591 14.74211121 0.6633091 166.44288635 14.54141235
		 0.55580199 165.98571777 14.76255798 0.70561302 166.2038269 14.68727112 0.8993665 165.76924133 15.11010742
		 1.013001323 166.40982056 14.94929504 1.10701835 166.89076233 14.32794189 0.94355309 166.87640381 14.2651062
		 1.38796401 168.46330261 13.83856201 1.36692524 167.16119385 14.40576172 1.58287632 168.56918335 13.92753601
		 3.048388958 167.91191101 13.54811096 1.90904319 166.85470581 14.22612 1.26210904 165.63928223 15.055175781
		 1.095930576 164.80966187 14.97865295 0.94394833 164.69195557 15.31784058 0.30999795 165.5189209 15.46401978
		 0.22961298 165.62815857 15.18667603 -0.1286803 165.31985474 15.57337952 0.010229427 164.055053711 15.94140625
		 0.0095456988 162.05015564 16.74945068 0.66898406 162.10383606 15.54772949 -0.55215895 163.28636169 15.82752991
		 -0.9010964 164.64138794 15.34030151 -0.99741369 163.93486023 15.25186157 -1.020286441 164.76231384 15.15008545
		 -0.96875507 164.10693359 15.18013 -1.073313832 164.80091858 14.98620605 -0.78231508 164.2303772 14.80172729
		 -0.80120021 164.099029541 14.83821106 -1.51345313 166.35466003 13.79824829 -2.23353863 166.77964783 13.58558655
		 -2.86361265 167.15263367 13.72033691 -2.56005192 166.97962952 13.38916016 -3.38208556 167.21453857 13.012268066
		 -1.1840179 163.45095825 14.93261719 -1.11276245 163.52041626 15.10223389 -1.51327538 163.22792053 14.99911499
		 -1.40379214 163.22872925 15.10978699 -1.51947427 162.88510132 15.33024597 -1.3769455 162.88638306 15.2973175
		 -1.15778399 163.37254333 15.11573792 -1.10971642 162.027618408 15.54423523 -0.65127802 162.10098267 15.54304504
		 -1.3561244 162.092605591 15.75395203 -1.84705758 162.91978455 15.53581238 -1.96361423 162.34298706 15.60800171
		 2.48900223 169.43019104 13.23609924 2.058299065 172.63893127 11.8765564 1.80410695 170.27996826 13.10491943
		 1.17140436 172.26783752 12.42112732 1.12522399 170.81947327 13.084579468 0.99737084 172.55610657 12.16938782
		 1.001003027 173.47744751 11.52127075 0.85950458 172.80726624 12.045333862 0.93313116 174.49508667 10.72828674
		 0.05688028 173.83557129 12.24180603 0.08344727 175.67144775 10.61109924 -0.0032031077 173.85676575 12.26341248
		 0.056378584 171.81381226 13.42605591 -0.0090910364 171.79327393 13.4671936 0.059105087 169.45573425 14.53321838
		 0.87207103 170.58395386 13.18916321 0.90646213 168.87831116 13.91046143 0.97165197 170.61682129 13.13624573
		 1.17902422 168.87301636 13.86149597 1.063151479 168.60469055 13.84489441 0.91640431 167.095001221 14.22996521
		 0.7008884 167.20158386 14.5266571 -0.0034560682 169.48106384 14.55735779;
	setAttr ".vt[2324:2471]" -0.87853479 170.54074097 13.18331909 -0.09942688 167.51219177 14.90441895
		 -0.86976498 172.79566956 12.018508911 -1.062679291 170.64178467 13.14001465 -1.13299775 170.60829163 13.16670227
		 -1.77377295 170.28785706 13.10549927 -1.14403653 172.25007629 12.43389893 -1.20815647 173.6839447 11.52897644
		 -1.00022912025 173.15246582 11.7885437 -1.029909015 174.5067749 10.68504333 -1.13466299 174.55227661 10.68238831
		 -1.24130857 174.75117493 10.53538513 -1.21736586 175.28039551 9.88789368 -0.99909699 175.14776611 9.77706909
		 -1.25911915 175.24969482 9.1541748 -1.17486203 175.2244873 9.10307312 -1.058598638 175.29023743 9.072921753
		 -1.13520038 175.41838074 8.72486877 -1.0011662245 175.4420166 8.88014221 -1.10003221 175.68649292 8.35224915
		 -1.27253377 175.59915161 8.51014709 -1.13837969 175.84063721 8.36425781 -0.95858252 175.79646301 8.43234253
		 -0.89660299 176.13601685 8.18592834 -0.59045804 176.58358765 8.24668884 -0.85065782 176.54988098 8.016311646
		 -0.53438884 177.52069092 6.77854919 -1.1599735 176.32354736 8.1414032 -1.50217903 175.82347107 8.8301239
		 -1.11909044 176.13546753 8.24740601 0.0079466756 177.45327759 7.81748962 -0.11164279 178.16639709 6.04649353
		 -0.48666316 178.12182617 4.90742493 -0.013278573 178.72561646 3.059036255 0.15552859 178.14761353 6.047653198
		 0.5116905 178.10624695 4.95613098 0.58957112 177.50039673 6.75245667 0.5855481 177.11958313 7.4044342
		 1.049554586 176.47070313 8.023376465 1.031868458 177.39476013 6.25057983 0.96617228 177.89477539 4.44628906
		 0.65105766 176.60575867 8.1439209 0.96111912 176.022277832 8.23100281 1.11480224 176.24539185 8.22543335
		 1.18715 175.67405701 8.36590576 1.10240901 175.58462524 8.48652649 1.28189087 175.48242188 8.6289978
		 1.33507383 175.66499329 8.46841431 1.42212832 175.49769592 8.81782532 1.26832533 175.22453308 9.15037537
		 1.32670367 175.3928833 9.56626892 1.61694741 175.51422119 9.40939331 1.44345129 175.11546326 10.027801514
		 1.21619034 175.26416016 9.91212463 1.24913836 174.7411499 10.54742432 1.078936934 174.89263916 10.1809082
		 1.091507792 174.47373962 10.71705627 0.99106538 175.12754822 9.78074646 0.83359462 174.72344971 10.59759521
		 0.84543723 175.22262573 9.71624756 1.052050114 175.15092468 9.473526 1.02441299 175.42680359 8.89498901
		 1.15884674 175.25085449 9.047958374 0.0095541161 176.65252686 9.14428711 -0.017177111 175.74615479 10.59083557
		 -0.88992465 174.56596375 10.6965332 -0.84765172 175.14291382 9.8140564 -0.85458761 173.28175354 11.68891907
		 -1.005841732 172.489151 12.21298218 1.22773993 173.69560242 11.52099609 1.75875235 174.15003967 10.94296265
		 1.46979189 175.85522461 8.74655151 -1.73665559 174.15092468 10.9440918 -6.50900698 169.28366089 9.38967896
		 -8.72541618 170.70092773 2.7958374 -8.86124992 170.52844238 1.81855774 -8.29673004 170.86875916 2.55082703
		 4.52119732 167.083007813 12.30888367 -0.6639688 163.40823364 14.82678223 -0.83755827 162.59089661 15.17028809
		 -1.32573414 163.041488647 14.92417908 -0.80120021 164.099029541 14.83821106 -1.1840179 163.45095825 14.93261719
		 -1.51327538 163.22792053 14.99911499 0.043950096 162.073196411 15.24673462 0.090294816 161.33561707 15.45915222
		 2.36152244 161.090148926 15.18673706 3.093956947 161.46942139 14.9262085 3.67303705 161.73513794 14.38383484
		 4.083234787 161.97483826 14.010513306 3.59419727 163.10087585 14.087310791 3.71700168 163.25947571 14.10038757
		 3.91861892 163.31144714 14.065826416 3.21744061 163.46836853 14.68429565 4.31171608 163.25767517 13.89227295
		 4.36747074 162.88935852 14.46739197 5.39480639 163.03263855 13.57165527 5.28198433 162.63519287 13.76274109
		 5.26110077 162.40922546 13.74290466 3.28971291 163.03302002 15.058227539 5.16082287 162.17758179 13.93502808
		 3.93750858 161.78140259 14.8404541 5.11323929 161.87130737 13.9344635 4.08528614 161.75364685 14.69482422
		 4.65613747 161.76333618 13.71014404 4.075489998 161.72709656 14.2177887 3.49323535 161.58055115 14.68717957
		 3.67303705 161.73513794 14.38383484 3.56600952 161.61175537 15.056472778 4.083234787 161.97483826 14.010513306
		 2.43335962 163.11064148 15.37490845 1.97557855 162.35081482 15.60974121 2.3825345 163.42645264 15.0028686523
		 0.53766304 159.47499084 16.3400116 -2.11609817 161.89004517 15.27845764 -2.39112926 162.3454895 15.42124939
		 -2.58085513 162.025543213 15.41862488 -2.8579731 162.20115662 15.32475281 -3.16654253 161.48419189 15.3183136
		 -3.14497089 161.43759155 15.26023865 -3.077823162 161.47540283 14.91419983 -2.96821547 161.65596008 14.76274109
		 -1.91853046 161.46391296 14.98144531 -2.63540578 163.20019531 14.50701904 -1.63302469 162.68629456 14.88128662
		 -1.12064433 161.21932983 15.45458984 -1.018865347 162.20211792 15.2184906 -1.32573414 163.041488647 14.92417908
		 -0.83755827 162.59089661 15.17028809 0.090294816 161.33561707 15.45915222 -2.27300072 163.42521667 14.75180054
		 -1.51327538 163.22792053 14.99911499 -0.96882588 155.65090942 16.44776917 -1.47395074 156.19644165 16.42037964
		 -1.372949 158.097518921 15.90097046 0.22426696 155.75975037 16.36698914 0.80521643 155.50979614 16.46202087
		 1.48919249 156.20111084 16.41290283 1.3856951 158.071380615 15.9024353 -0.083640933 158.17152405 15.90419006
		 0.036086157 159.84020996 15.65621948 1.82336533 160.68304443 15.95474243 2.36152244 161.090148926 15.18673706
		 1.70361602 160.67256165 15.46557617 1.64026904 158.65010071 15.86376953 1.48919249 156.20111084 16.41290283
		 1.3856951 158.071380615 15.9024353 0.036086157 159.84020996 15.65621948;
	setAttr -s 7183 ".ed";
	setAttr ".ed[0:165]"  0 1 1 1 2 1 2 0 1 1 3 1 3 2 1 3 4 1 4 2 1 4 5 1 5 2 1
		 4 6 1 6 5 1 6 7 1 7 5 1 7 8 1 8 5 1 8 9 1 9 5 1 0 5 1 9 0 1 9 10 1 10 0 1 10 11 1
		 11 0 1 12 11 1 10 12 1 8 12 1 10 8 1 12 13 1 13 11 1 13 14 1 14 11 1 14 15 1 15 11 1
		 14 16 1 16 15 1 16 17 1 17 15 1 18 15 1 17 18 1 17 19 1 19 18 1 19 20 1 20 18 1 20 21 1
		 21 18 1 20 22 1 22 21 1 20 23 1 23 22 1 23 24 1 24 22 1 25 24 1 23 25 1 23 26 1 26 25 1
		 26 27 1 27 25 1 28 25 1 27 28 1 29 28 1 27 29 1 27 30 1 30 29 1 30 31 1 31 29 1 3 29 1
		 31 3 1 30 32 1 32 31 1 32 33 1 33 31 1 32 34 1 34 33 1 32 35 1 35 34 1 35 36 1 36 34 1
		 37 34 1 36 37 1 36 38 1 38 37 1 39 38 1 36 39 1 40 38 1 39 40 1 41 40 1 39 41 1 39 35 1
		 35 41 1 42 41 1 35 42 1 42 43 1 43 41 1 43 44 1 44 41 1 44 45 1 45 41 1 44 46 1 46 45 1
		 44 47 1 47 46 1 47 48 1 48 46 1 48 40 1 40 46 1 48 49 1 49 40 1 50 49 1 48 50 1 51 50 1
		 48 51 1 51 38 1 38 50 1 51 52 1 52 38 1 51 53 1 53 52 1 53 54 1 54 52 1 54 55 1 55 52 1
		 56 52 1 55 56 1 57 56 1 55 57 1 58 57 1 55 58 1 55 59 1 59 58 1 59 60 1 60 58 1 59 61 1
		 61 60 1 61 62 1 62 60 1 61 63 1 63 62 1 63 64 1 64 62 1 63 65 1 65 64 1 65 66 1 66 64 1
		 65 67 1 67 66 1 67 68 1 68 66 0 67 69 1 69 68 1 69 70 1 70 68 0 71 70 1 69 71 1 72 71 1
		 69 72 1 73 72 1 69 73 1 74 72 1 73 74 1 73 75 1 75 74 1 76 75 1 73 76 1 73 67 1 67 76 1
		 63 75 1;
	setAttr ".ed[166:331]" 76 63 1 63 77 1 77 75 1 77 78 1 78 75 1 79 78 1 77 79 1
		 59 79 1 77 59 1 80 79 1 59 80 1 59 81 1 81 80 1 54 81 1 59 54 1 54 82 1 82 81 1 82 80 1
		 83 80 1 82 83 1 84 83 1 82 84 1 82 85 1 85 84 1 82 51 1 51 85 1 51 47 1 47 85 1 47 86 1
		 86 85 1 87 86 1 47 87 1 88 87 1 47 88 1 47 89 1 89 88 1 89 90 1 90 88 1 91 88 1 90 91 1
		 92 91 1 90 92 1 93 92 1 90 93 1 90 94 1 94 93 1 90 95 1 95 94 1 95 96 1 96 94 1 97 94 1
		 96 97 1 96 98 1 98 97 1 98 99 1 99 97 1 100 97 1 99 100 1 101 100 1 99 101 1 102 101 1
		 99 102 1 103 102 1 99 103 1 104 103 1 99 104 1 27 103 1 104 27 1 27 102 1 102 105 1
		 105 101 1 106 101 1 105 106 1 105 107 1 107 106 1 107 108 1 108 106 1 108 109 1 109 106 1
		 108 110 1 110 109 1 111 109 1 110 111 1 112 111 1 110 112 1 113 112 1 110 113 1 114 113 1
		 110 114 1 110 115 1 115 114 1 116 115 1 110 116 1 110 117 1 117 116 1 118 116 1 117 118 1
		 119 118 1 117 119 1 117 120 1 120 119 1 120 121 1 121 119 1 122 119 1 121 122 1 121 123 1
		 123 122 1 123 124 1 124 122 1 125 122 1 124 125 1 124 126 0 126 125 1 126 127 1 127 125 1
		 127 128 1 128 125 1 128 129 1 129 125 1 128 118 1 118 129 1 128 130 1 130 118 1 131 118 1
		 130 131 1 130 132 1 132 131 1 132 133 1 133 131 1 133 115 1 115 131 1 133 134 0 134 115 1
		 134 135 1 135 115 1 134 136 1 136 135 1 136 137 1 137 135 1 137 138 1 138 135 1 139 138 1
		 137 139 0 139 140 0 140 138 1 141 138 1 140 141 1 140 142 1 142 141 1 142 143 1 143 141 1
		 144 141 1 143 144 1 143 145 1 145 144 1 145 146 1 146 144 1 147 144 1 146 147 1 146 148 1
		 148 147 1 148 149 1 149 147 1 148 150 1 150 149 1 150 151 1;
	setAttr ".ed[332:497]" 151 149 1 151 152 1 152 149 1 151 153 1 153 152 1 154 152 1
		 153 154 1 153 155 1 155 154 1 153 156 1 156 155 1 157 155 1 156 157 1 156 158 1 158 157 1
		 159 157 1 158 159 1 158 160 1 160 159 1 161 159 1 160 161 1 160 162 1 162 161 1 163 162 1
		 160 163 1 160 164 1 164 163 1 164 165 1 165 163 1 166 163 1 165 166 1 165 167 1 167 166 1
		 167 168 1 168 166 1 169 166 1 168 169 1 170 169 1 168 170 1 171 170 1 168 171 1 171 172 1
		 172 170 1 172 173 1 173 170 1 174 170 1 173 174 1 175 174 1 173 175 1 173 176 1 176 175 1
		 176 177 1 177 175 1 177 178 1 178 175 1 179 175 1 178 179 1 180 179 1 178 180 1 181 180 1
		 178 181 1 181 182 1 182 180 1 183 180 1 182 183 1 184 183 1 182 184 1 182 185 1 185 184 1
		 186 184 1 185 186 1 187 186 1 185 187 1 188 186 1 187 188 1 187 189 1 189 188 1 189 190 1
		 190 188 1 191 188 1 190 191 1 190 192 1 192 191 1 192 193 1 193 191 1 193 194 1 194 191 1
		 195 191 1 194 195 1 194 196 1 196 195 1 197 195 1 196 197 1 196 198 1 198 197 1 198 199 1
		 199 197 1 198 184 1 184 199 1 198 200 1 200 184 1 198 201 1 201 200 1 201 202 1 202 200 1
		 202 203 1 203 200 1 202 204 1 204 203 1 204 205 1 205 203 1 205 206 1 206 203 1 206 207 1
		 207 203 1 206 208 1 208 207 1 206 209 1 209 208 1 209 210 1 210 208 1 210 211 1 211 208 1
		 212 211 1 210 212 1 213 212 1 210 213 1 210 214 1 214 213 1 215 214 1 210 215 1 210 216 1
		 216 215 1 217 215 1 216 217 1 205 217 1 216 205 1 205 218 1 218 217 1 218 219 1 219 217 1
		 218 220 1 220 219 1 218 221 1 221 220 1 221 222 1 222 220 1 223 220 1 222 223 1 222 224 1
		 224 223 1 225 223 1 224 225 1 226 225 1 224 226 1 227 226 1 224 227 1 224 221 1 221 227 1
		 228 227 1 221 228 1 229 228 1 221 229 1 221 230 1 230 229 1 202 229 1;
	setAttr ".ed[498:663]" 230 202 1 231 228 1 229 231 1 232 231 1 229 232 1 201 232 1
		 229 201 1 233 232 1 201 233 1 196 233 1 201 196 1 233 234 1 234 232 1 234 235 1 235 232 1
		 235 236 1 236 232 1 235 237 1 237 236 1 237 238 1 238 236 1 238 231 1 231 236 1 238 239 1
		 239 231 1 238 240 1 240 239 1 240 241 1 241 239 1 241 227 1 227 239 1 240 242 1 242 241 1
		 242 243 1 243 241 1 243 226 1 226 241 1 242 244 1 244 243 1 242 245 1 245 244 1 245 246 1
		 246 244 1 245 247 1 247 246 1 247 248 1 248 246 1 248 249 1 249 246 1 249 250 1 250 246 1
		 249 251 1 251 250 1 251 252 1 252 250 1 251 253 1 253 252 1 253 254 1 254 252 1 253 255 1
		 255 254 1 256 254 1 255 256 1 255 257 1 257 256 1 257 258 1 258 256 1 258 259 1 259 256 1
		 258 260 1 260 259 1 260 254 1 254 259 1 260 261 1 261 254 1 262 254 1 261 262 1 261 263 1
		 263 262 1 264 263 1 261 264 1 261 265 1 265 264 1 265 266 1 266 264 1 265 267 1 267 266 1
		 265 258 1 258 267 1 267 268 1 268 266 1 269 266 1 268 269 1 268 270 1 270 269 1 268 271 1
		 271 270 1 272 270 1 271 272 1 273 272 1 271 273 1 274 272 1 273 274 1 275 274 1 273 275 1
		 276 275 1 273 276 1 273 277 1 277 276 1 277 278 1 278 276 1 277 279 1 279 278 1 279 280 1
		 280 278 1 280 281 1 281 278 1 281 282 1 282 278 1 281 283 1 283 282 1 283 284 1 284 282 1
		 284 276 1 276 282 1 283 285 1 285 284 1 285 286 1 286 284 1 286 287 1 287 284 1 288 284 1
		 287 288 1 287 289 1 289 288 1 289 290 1 290 288 1 290 291 1 291 288 1 274 288 1 291 274 1
		 290 292 1 292 291 1 293 291 1 292 293 1 294 293 1 292 294 1 292 295 1 295 294 1 292 296 1
		 296 295 1 296 297 1 297 295 1 296 298 1 298 297 1 299 297 1 298 299 1 298 289 1 289 299 1
		 299 300 1 300 297 1 301 297 1 300 301 1 300 302 1 302 301 1 302 303 1;
	setAttr ".ed[664:829]" 303 301 1 304 301 1 303 304 1 305 304 1 303 305 1 303 306 1
		 306 305 1 307 305 1 306 307 1 306 308 1 308 307 1 309 307 1 308 309 1 308 310 1 310 309 1
		 310 311 1 311 309 1 310 312 1 312 311 1 312 313 1 313 311 1 314 311 1 313 314 1 313 315 1
		 315 314 1 315 316 1 316 314 1 317 314 1 316 317 1 318 317 1 316 318 1 316 319 1 319 318 1
		 320 318 1 319 320 1 319 321 1 321 320 1 319 322 1 322 321 1 322 323 1 323 321 1 324 321 1
		 323 324 1 323 325 1 325 324 1 326 324 1 325 326 1 325 327 1 327 326 1 327 328 1 328 326 1
		 329 326 1 328 329 1 320 329 1 328 320 1 328 330 1 330 320 1 331 330 1 328 331 1 332 331 1
		 328 332 1 328 333 1 333 332 1 333 334 1 334 332 1 335 332 1 334 335 1 336 335 1 334 336 1
		 334 337 1 337 336 1 337 338 1 338 336 1 337 339 1 339 338 1 339 340 1 340 338 1 341 338 1
		 340 341 1 340 342 1 342 341 1 343 341 1 342 343 1 342 344 1 344 343 1 342 345 1 345 344 1
		 342 346 1 346 345 1 342 347 1 347 346 1 347 348 1 348 346 1 347 349 1 349 348 1 347 350 1
		 350 349 1 350 351 1 351 349 0 352 351 1 350 352 1 350 353 1 353 352 1 350 354 1 354 353 1
		 354 355 1 355 353 1 355 356 1 356 353 1 355 357 1 357 356 1 357 358 1 358 356 1 358 359 1
		 359 356 1 352 356 1 359 352 1 360 352 1 359 360 1 359 361 1 361 360 1 362 361 1 359 362 1
		 359 363 1 363 362 1 363 364 1 364 362 1 364 365 1 365 362 0 364 366 1 366 365 0 364 367 1
		 367 366 1 367 368 1 368 366 1 369 366 0 368 369 1 370 369 1 368 370 1 368 371 1 371 370 1
		 371 372 1 372 370 1 371 373 1 373 372 1 374 372 1 373 374 1 373 375 1 375 374 1 375 376 1
		 376 374 1 377 374 1 376 377 1 378 377 0 376 378 1 376 379 1 379 378 1 379 380 1 380 378 1
		 380 381 1 381 378 0 380 382 1 382 381 0 379 382 1 379 383 1 383 382 1;
	setAttr ".ed[830:995]" 383 384 1 384 382 1 384 385 1 385 382 1 384 386 1 386 385 1
		 387 385 0 386 387 1 386 388 1 388 387 1 389 387 1 388 389 1 390 389 1 388 390 1 391 390 1
		 388 391 1 392 391 1 388 392 1 393 392 1 388 393 1 394 393 1 388 394 1 395 394 1 388 395 1
		 396 395 1 388 396 1 397 396 1 388 397 1 397 398 1 398 396 1 399 396 1 398 399 1 398 383 1
		 383 399 1 383 400 1 400 399 1 400 401 1 401 399 1 401 402 1 402 399 1 401 403 1 403 402 1
		 403 404 1 404 402 1 404 405 1 405 402 1 405 395 1 395 402 1 405 406 1 406 395 1 405 407 1
		 407 406 1 407 408 1 408 406 1 408 409 1 409 406 1 408 410 1 410 409 1 410 392 1 392 409 1
		 408 411 1 411 410 1 412 410 1 411 412 1 411 413 1 413 412 1 413 414 1 414 412 1 389 412 1
		 414 389 1 415 389 1 414 415 1 414 416 1 416 415 0 414 417 1 417 416 0 414 418 1 418 417 1
		 418 419 1 419 417 0 418 420 1 420 419 1 420 421 1 421 419 1 420 422 1 422 421 1 422 423 1
		 423 421 1 423 424 1 424 421 1 423 425 1 425 424 1 426 424 1 425 426 1 427 426 1 425 427 1
		 428 427 1 425 428 1 425 429 1 429 428 1 430 428 1 429 430 1 429 431 1 431 430 1 431 432 1
		 432 430 1 433 430 1 432 433 1 432 434 1 434 433 1 434 435 1 435 433 1 435 436 1 436 433 1
		 436 437 1 437 433 1 437 438 1 438 433 1 428 438 1 437 428 1 437 439 0 439 428 1 436 440 1
		 440 437 1 440 441 1 441 437 0 440 442 1 442 441 1 442 443 1 443 441 0 442 444 1 444 443 0
		 442 445 1 445 444 0 442 446 1 446 445 1 446 447 1 447 445 0 448 447 1 446 448 1 446 449 1
		 449 448 1 449 450 1 450 448 1 450 451 1 451 448 1 450 452 1 452 451 1 452 453 1 453 451 1
		 453 454 1 454 451 1 455 454 1 453 455 1 453 456 1 456 455 1 453 457 1 457 456 1 457 458 1
		 458 456 1 458 459 1 459 456 1 459 460 1 460 456 1 461 456 1 460 461 1;
	setAttr ".ed[996:1161]" 460 462 1 462 461 1 463 461 1 462 463 1 464 463 1 462 464 1
		 462 465 1 465 464 0 464 466 0 466 463 1 466 467 1 467 463 1 466 468 1 468 467 1 468 469 1
		 469 467 1 468 470 1 470 469 1 470 471 1 471 469 1 471 472 0 472 469 1 472 473 1 473 469 1
		 472 474 0 474 473 1 474 455 1 455 473 1 474 475 0 475 455 1 470 476 1 476 471 0 470 477 1
		 477 476 0 470 478 1 478 477 1 479 477 0 478 479 1 480 479 0 478 480 1 478 481 1 481 480 0
		 478 468 1 468 481 1 468 482 1 482 481 0 483 482 0 468 483 1 473 467 1 473 461 1 461 467 1
		 466 483 0 460 465 1 473 456 1 459 465 1 484 465 0 459 484 1 459 485 1 485 484 1 486 484 0
		 485 486 1 487 486 0 485 487 1 488 487 0 485 488 1 485 489 1 489 488 0 490 489 0 485 490 1
		 459 490 1 459 491 1 491 490 0 458 491 1 458 492 1 492 491 1 493 491 0 492 493 1 494 493 0
		 492 494 1 492 495 1 495 494 1 492 496 1 496 495 1 497 495 1 496 497 1 496 498 1 498 497 0
		 496 499 1 499 498 1 500 499 1 496 500 1 501 500 1 496 501 1 496 458 1 458 501 1 501 502 1
		 502 500 1 501 457 1 457 502 1 452 502 1 457 452 1 502 499 1 502 450 1 450 499 1 450 503 1
		 503 499 1 450 504 1 504 503 1 498 503 1 504 498 0 497 494 0 475 454 1 448 454 1 475 448 1
		 449 504 1 449 505 1 505 504 1 506 505 1 449 506 1 507 506 1 449 507 1 507 508 1 508 506 1
		 509 506 1 508 509 1 510 509 1 508 510 1 508 511 1 511 510 0 512 511 1 508 512 1 513 511 0
		 512 513 1 514 513 1 512 514 1 507 514 1 512 507 1 515 514 1 507 515 1 446 515 1 507 446 1
		 446 516 1 516 515 1 517 515 1 516 517 1 516 518 1 518 517 1 518 519 1 519 517 1 519 514 1
		 514 517 1 519 520 1 520 514 1 520 521 1 521 514 1 522 521 1 520 522 1 520 523 1 523 522 1
		 523 524 1 524 522 1 524 525 1 525 522 1 526 522 1 525 526 1 527 526 1;
	setAttr ".ed[1162:1327]" 525 527 1 525 528 1 528 527 1 528 529 1 529 527 1 530 527 1
		 529 530 1 529 531 1 531 530 1 531 532 1 532 530 1 532 533 1 533 530 1 533 534 1 534 530 1
		 535 534 1 533 535 1 533 536 1 536 535 1 536 537 1 537 535 1 537 538 1 538 535 1 539 538 1
		 537 539 1 540 539 1 537 540 1 537 541 1 541 540 1 542 541 1 537 542 1 542 543 1 543 541 1
		 544 541 1 543 544 0 544 545 0 545 541 1 542 546 1 546 543 1 546 547 1 547 543 0 546 548 1
		 548 547 1 549 548 1 546 549 1 546 550 1 550 549 1 550 551 1 551 549 1 551 552 1 552 549 1
		 551 553 1 553 552 1 553 554 1 554 552 1 555 554 1 553 555 1 556 555 1 553 556 1 557 555 1
		 556 557 1 551 557 1 556 551 1 551 558 1 558 557 1 532 557 1 558 532 1 532 559 1 559 557 1
		 532 560 1 560 559 1 560 561 1 561 559 1 560 562 1 562 561 1 562 563 1 563 561 1 563 564 1
		 564 561 1 563 565 1 565 564 1 565 566 1 566 564 1 566 567 1 567 564 1 567 568 1 568 564 1
		 568 569 1 569 564 1 570 569 1 568 570 1 571 570 1 568 571 1 568 572 1 572 571 1 572 573 1
		 573 571 1 554 571 1 573 554 1 573 574 1 574 554 1 575 554 1 574 575 1 576 575 1 574 576 1
		 574 577 1 577 576 1 577 578 1 578 576 0 577 579 1 579 578 1 579 580 1 580 578 0 579 581 1
		 581 580 1 581 582 1 582 580 0 581 583 1 583 582 1 584 582 1 583 584 1 583 585 1 585 584 1
		 583 586 1 586 585 1 586 587 1 587 585 1 586 588 1 588 587 1 588 589 1 589 587 1 589 590 1
		 590 587 1 590 591 1 591 587 1 592 591 1 590 592 1 593 592 1 590 593 1 593 594 1 594 592 1
		 595 592 1 594 595 1 594 596 1 596 595 1 597 595 1 596 597 1 596 598 1 598 597 1 598 599 1
		 599 597 1 599 600 1 600 597 1 600 601 1 601 597 1 601 602 0 602 597 1 602 603 1 603 597 1
		 587 597 1 603 587 1 604 587 1 603 604 1 602 604 1 602 605 0 605 604 1;
	setAttr ".ed[1328:1493]" 605 584 1 584 604 1 600 606 1 606 601 0 599 606 1 599 607 1
		 607 606 0 608 607 1 599 608 1 609 608 1 599 609 1 599 610 1 610 609 1 610 611 1 611 609 1
		 610 612 1 612 611 1 610 613 1 613 612 1 614 613 1 610 614 1 610 615 1 615 614 1 615 616 1
		 616 614 1 616 617 1 617 614 1 617 618 1 618 614 1 617 619 1 619 618 1 619 613 1 613 618 1
		 620 613 1 619 620 1 621 620 1 619 621 1 622 621 1 619 622 1 619 623 1 623 622 1 624 622 1
		 623 624 1 623 625 1 625 624 1 626 624 1 625 626 1 625 627 1 627 626 1 627 628 1 628 626 1
		 627 629 1 629 628 1 630 628 1 629 630 1 629 631 1 631 630 1 632 630 1 631 632 1 633 632 1
		 631 633 1 631 634 1 634 633 1 631 635 1 635 634 1 635 636 1 636 634 1 635 637 1 637 636 1
		 637 638 1 638 636 1 637 639 1 639 638 1 639 640 1 640 638 1 641 640 1 639 641 1 639 642 1
		 642 641 1 642 643 1 643 641 1 643 644 1 644 641 1 645 641 1 644 645 1 644 646 1 646 645 1
		 646 647 1 647 645 1 646 648 1 648 647 1 648 649 1 649 647 1 648 650 1 650 649 1 650 651 1
		 651 649 1 650 652 1 652 651 1 653 651 1 652 653 1 652 654 1 654 653 1 654 640 1 640 653 1
		 654 655 1 655 640 1 654 656 1 656 655 1 656 657 1 657 655 1 657 638 1 638 655 1 652 657 1
		 656 652 1 652 658 1 658 657 1 658 659 1 659 657 1 659 660 1 660 657 1 634 657 1 660 634 1
		 661 660 1 659 661 1 662 661 1 659 662 1 663 662 1 659 663 1 659 664 1 664 663 1 664 665 1
		 665 663 1 665 666 1 666 663 1 666 667 1 667 663 1 666 668 1 668 667 1 668 669 1 669 667 1
		 669 670 1 670 667 1 670 662 1 662 667 1 669 671 1 671 670 1 671 672 1 672 670 1 672 673 1
		 673 670 1 661 670 1 673 661 1 673 674 1 674 661 1 675 674 1 673 675 1 675 676 1 676 674 1
		 676 677 1 677 674 1 677 678 1 678 674 1 677 679 1 679 678 1 679 633 1;
	setAttr ".ed[1494:1659]" 633 678 1 679 680 1 680 633 1 680 681 1 681 633 1 681 682 1
		 682 633 1 682 683 1 683 633 1 682 684 1 684 683 1 684 632 1 632 683 1 685 632 1 684 685 1
		 686 685 1 684 686 1 687 686 1 684 687 1 684 688 1 688 687 1 688 689 1 689 687 1 689 690 1
		 690 687 1 689 691 1 691 690 1 691 692 1 692 690 1 692 608 1 608 690 1 611 690 1 608 611 1
		 693 690 1 611 693 1 693 686 1 686 690 1 692 694 1 694 608 1 692 695 1 695 694 1 692 696 1
		 696 695 1 696 697 1 697 695 1 696 698 1 698 697 1 698 699 1 699 697 1 700 697 1 699 700 1
		 699 701 1 701 700 1 701 702 1 702 700 1 701 703 1 703 702 1 703 704 1 704 702 1 704 705 1
		 705 702 1 705 706 1 706 702 1 705 707 1 707 706 0 708 702 1 706 708 0 708 697 1 697 702 1
		 694 697 1 708 694 1 708 709 1 709 694 1 709 710 1 710 694 1 709 607 1 607 710 1 708 607 0
		 704 707 1 704 711 1 711 707 0 704 712 1 712 711 1 712 713 1 713 711 1 712 714 1 714 713 1
		 714 715 1 715 713 1 716 713 1 715 716 1 715 717 1 717 716 1 717 718 1 718 716 0 717 719 1
		 719 718 0 717 720 1 720 719 1 720 721 1 721 719 1 721 722 1 722 719 1 722 723 1 723 719 1
		 723 724 1 724 719 0 723 725 1 725 724 1 725 726 1 726 724 0 725 727 1 727 726 1 727 728 1
		 728 726 1 728 729 1 729 726 0 728 730 1 730 729 1 731 729 0 730 731 1 730 732 1 732 731 0
		 730 733 1 733 732 1 733 734 1 734 732 0 735 734 1 733 735 1 733 736 1 736 735 1 736 737 1
		 737 735 1 737 738 1 738 735 1 737 739 1 739 738 1 740 739 1 737 740 1 741 740 1 737 741 1
		 741 742 1 742 740 1 743 742 1 741 743 1 744 743 1 741 744 1 741 736 1 736 744 1 745 744 1
		 736 745 1 736 746 1 746 745 1 747 745 1 746 747 1 746 748 1 748 747 1 749 748 1 746 749 1
		 746 733 1 733 749 1 750 749 1 733 750 1 750 748 1 750 730 1 730 748 1;
	setAttr ".ed[1660:1825]" 751 747 1 748 751 1 752 751 1 748 752 1 748 728 1 728 752 1
		 727 751 1 752 727 1 727 753 1 753 751 1 753 754 1 754 751 1 755 754 1 753 755 1 753 756 1
		 756 755 1 756 757 1 757 755 1 756 758 1 758 757 1 758 759 1 759 757 1 754 757 1 759 754 1
		 760 754 1 759 760 1 759 761 1 761 760 1 761 762 1 762 760 1 761 763 1 763 762 1 763 743 1
		 743 762 1 763 764 1 764 743 1 764 765 1 765 743 1 764 766 1 766 765 1 766 767 1 767 765 1
		 768 765 1 767 768 1 767 769 1 769 768 1 769 770 1 770 768 1 771 768 1 770 771 1 770 772 1
		 772 771 1 773 771 1 772 773 1 774 773 1 772 774 1 772 767 1 767 774 1 775 773 1 774 775 1
		 766 775 1 774 766 1 766 776 1 776 775 1 776 763 1 763 775 1 763 777 1 777 775 1 763 778 1
		 778 777 1 779 778 1 763 779 1 759 779 1 763 759 1 780 779 1 759 780 1 780 778 1 780 781 1
		 781 778 1 782 781 1 780 782 1 780 758 1 758 782 1 758 783 1 783 782 1 783 784 1 784 782 1
		 783 727 1 727 784 1 727 723 1 723 784 1 722 782 1 784 722 1 722 785 1 785 782 1 785 786 1
		 786 782 1 785 787 1 787 786 1 787 788 1 788 786 1 788 789 1 789 786 1 789 790 1 790 786 1
		 777 786 1 790 777 1 790 773 1 773 777 1 790 791 1 791 773 1 790 792 1 792 791 1 792 793 1
		 793 791 1 794 793 1 792 794 1 789 794 1 792 789 1 789 795 1 795 794 1 796 794 1 795 796 1
		 797 796 1 795 797 1 798 797 1 795 798 1 799 797 1 798 799 1 798 800 1 800 799 1 800 801 1
		 801 799 1 800 802 1 802 801 1 803 801 1 802 803 1 804 803 1 802 804 1 805 804 1 802 805 1
		 806 805 1 802 806 1 807 805 1 806 807 1 806 808 1 808 807 1 806 809 1 809 808 1 809 810 1
		 810 808 1 810 720 1 720 808 1 810 811 1 811 720 1 811 812 1 812 720 1 812 813 1 813 720 1
		 813 814 1 814 720 1 815 814 1 813 815 1 816 815 1 813 816 1 816 798 1;
	setAttr ".ed[1826:1991]" 798 815 1 817 815 1 798 817 1 798 788 1 788 817 1 817 814 1
		 817 721 1 721 814 1 817 785 1 785 721 1 812 816 1 812 800 1 800 816 1 811 800 1 818 800 1
		 811 818 1 811 809 1 809 818 1 806 800 1 818 806 1 808 819 1 819 807 1 820 807 1 819 820 1
		 821 820 1 819 821 1 819 715 1 715 821 1 715 822 1 822 821 1 822 823 1 823 821 1 824 823 1
		 822 824 1 822 825 1 825 824 1 826 824 1 825 826 1 825 704 1 704 826 1 827 826 1 704 827 1
		 827 828 1 828 826 1 828 829 1 829 826 1 830 826 1 829 830 1 831 830 1 829 831 1 831 832 1
		 832 830 1 805 830 1 832 805 1 805 833 1 833 830 1 823 830 1 833 823 1 833 820 1 820 823 1
		 831 834 1 834 832 1 834 804 1 804 832 1 834 835 1 835 804 1 834 836 1 836 835 1 836 837 1
		 837 835 1 838 837 1 836 838 1 838 839 1 839 837 1 838 840 1 840 839 1 841 839 1 840 841 1
		 840 842 1 842 841 1 843 841 1 842 843 1 842 844 1 844 843 1 845 843 1 844 845 1 844 846 1
		 846 845 1 844 847 1 847 846 1 847 848 1 848 846 1 847 849 1 849 848 1 849 850 1 850 848 1
		 849 851 1 851 850 1 849 852 1 852 851 1 853 852 1 849 853 1 854 853 1 849 854 1 855 853 1
		 854 855 1 856 855 1 854 856 1 847 856 1 854 847 1 856 857 1 857 855 1 857 858 1 858 855 1
		 858 859 1 859 855 1 858 189 1 189 859 1 858 860 1 860 189 1 861 860 1 858 861 1 861 862 1
		 862 860 1 862 863 1 863 860 1 864 860 1 863 864 1 865 864 1 863 865 1 863 866 1 866 865 1
		 866 867 1 867 865 1 866 868 1 868 867 1 869 867 1 868 869 1 870 869 1 868 870 1 868 871 1
		 871 870 1 691 870 1 871 691 1 871 872 1 872 691 1 871 873 1 873 872 1 873 874 1 874 872 1
		 873 875 1 875 874 1 876 874 1 875 876 1 875 877 1 877 876 1 877 878 1 878 876 1 878 879 1
		 879 876 1 878 880 1 880 879 1 880 881 1 881 879 1 881 882 1 882 879 1;
	setAttr ".ed[1992:2157]" 699 879 1 882 699 1 881 883 1 883 882 1 883 884 1 884 882 1
		 884 701 1 701 882 1 883 885 1 885 884 1 885 886 1 886 884 1 886 703 1 703 884 1 886 827 1
		 827 703 1 885 828 1 828 886 1 885 831 1 831 828 1 885 887 1 887 831 1 883 887 1 888 887 1
		 883 888 1 888 889 1 889 887 1 889 834 1 834 887 1 889 838 1 838 834 1 888 838 1 881 888 1
		 881 890 1 890 888 1 890 891 1 891 888 1 891 840 1 840 888 1 890 892 1 892 891 1 892 856 1
		 856 891 1 842 891 1 856 842 1 893 892 1 890 893 1 890 880 1 880 893 1 893 878 1 878 892 1
		 698 876 1 879 698 1 877 892 1 877 894 1 894 892 1 894 861 1 861 892 1 861 857 1 857 892 1
		 862 894 1 877 862 1 875 862 1 698 874 1 873 866 1 866 875 1 874 696 1 696 872 1 691 895 1
		 895 870 1 895 896 1 896 870 1 896 897 1 897 870 1 896 898 1 898 897 1 899 897 1 898 899 1
		 898 900 1 900 899 1 901 899 1 900 901 1 900 902 1 902 901 1 902 192 1 192 901 1 192 867 1
		 867 901 1 192 864 1 864 867 1 900 903 1 903 902 1 903 904 1 904 902 1 903 905 1 905 904 1
		 905 906 1 906 904 1 906 907 1 907 904 1 907 193 1 193 904 1 906 234 1 234 907 1 194 907 1
		 234 194 1 905 908 1 908 906 1 908 909 1 909 906 1 909 235 1 235 906 1 908 910 1 910 909 1
		 908 911 1 911 910 1 911 912 1 912 910 1 913 912 1 911 913 1 914 913 1 911 914 1 911 915 1
		 915 914 1 916 914 1 915 916 1 915 917 1 917 916 1 915 918 1 918 917 1 918 919 1 919 917 1
		 919 920 1 920 917 1 921 917 1 920 921 1 920 922 1 922 921 1 922 923 1 923 921 1 923 924 1
		 924 921 1 924 925 1 925 921 1 925 916 1 916 921 1 924 926 1 926 925 1 927 926 1 924 927 1
		 928 926 1 927 928 1 929 928 1 927 929 1 927 930 1 930 929 1 927 931 1 931 930 1 927 923 1
		 923 931 1 923 932 1 932 931 1 932 933 1 933 931 1 933 671 1 671 931 1;
	setAttr ".ed[2158:2323]" 934 931 1 671 934 1 934 935 1 935 931 1 934 936 1 936 935 1
		 937 935 1 936 937 1 938 937 1 936 938 1 936 668 1 668 938 1 936 939 1 939 668 1 665 938 1
		 668 665 1 940 938 1 665 940 1 941 938 1 940 941 1 942 941 1 940 942 1 940 943 1 943 942 1
		 940 944 1 944 943 1 944 945 1 945 943 1 945 946 1 946 943 1 946 947 1 947 943 1 948 947 1
		 946 948 1 949 948 1 946 949 1 950 948 1 949 950 1 951 950 1 949 951 1 952 951 1 949 952 1
		 953 952 1 949 953 1 949 945 1 945 953 1 945 954 1 954 953 1 955 953 1 954 955 1 954 956 1
		 956 955 1 956 957 1 957 955 1 957 958 1 958 955 1 959 955 1 958 959 1 958 960 1 960 959 1
		 958 961 1 961 960 1 962 960 1 961 962 1 963 962 1 961 963 1 961 964 1 964 963 1 965 963 1
		 964 965 1 964 966 1 966 965 1 966 967 1 967 965 1 968 965 1 967 968 1 967 969 1 969 968 1
		 969 970 1 970 968 1 971 968 1 970 971 1 972 971 1 970 972 1 973 972 1 970 973 1 974 973 1
		 970 974 1 970 975 1 975 974 1 976 974 1 975 976 1 975 977 1 977 976 1 978 976 1 977 978 1
		 979 978 1 977 979 1 979 980 1 980 978 1 980 981 1 981 978 1 980 982 1 982 981 1 982 983 1
		 983 981 1 982 984 1 984 983 1 982 355 1 355 984 1 985 983 1 984 985 1 984 354 1 354 985 1
		 985 986 1 986 983 1 987 983 1 986 987 1 986 988 1 988 987 1 989 987 1 988 989 1 990 989 1
		 988 990 1 988 991 1 991 990 1 991 992 1 992 990 1 993 990 1 992 993 1 992 994 1 994 993 1
		 994 995 1 995 993 1 995 996 1 996 993 1 995 997 1 997 996 1 997 998 1 998 996 1 997 989 1
		 989 998 1 997 981 1 981 989 1 998 990 1 990 996 1 995 999 1 999 997 1 999 1000 1
		 1000 997 1 1000 1001 1 1001 997 1 976 997 1 1001 976 1 1000 974 1 974 1001 1 1000 1002 1
		 1002 974 1 1000 1003 1 1003 1002 1 1004 1002 1 1003 1004 1 1005 1004 1 1003 1005 1
		 1003 1006 1 1006 1005 1;
	setAttr ".ed[2324:2489]" 1006 1007 1 1007 1005 1 1007 999 1 999 1005 1 1007 1008 1
		 1008 999 1 1007 1009 1 1009 1008 1 1010 1008 1 1009 1010 1 1006 1010 1 1009 1006 1
		 1010 1000 1 1000 1008 1 1011 1005 1 999 1011 1 1012 1011 1 999 1012 1 999 992 1 992 1012 1
		 1013 1012 1 992 1013 1 992 1014 1 1014 1013 1 1015 1013 1 1014 1015 1 1014 327 1
		 327 1015 1 1014 1016 1 1016 327 1 1016 1017 1 1017 327 1 333 1017 1 1016 333 1 1016 1018 1
		 1018 333 1 1019 333 1 1018 1019 1 1018 1020 1 1020 1019 1 337 1019 1 1020 337 1 1018 1021 1
		 1021 1020 1 339 1020 1 1021 339 1 1021 1022 1 1022 339 1 1021 1023 1 1023 1022 1
		 1023 1024 1 1024 1022 1 1024 1025 1 1025 1022 1 991 1025 1 1024 991 1 991 340 1 340 1025 1
		 991 1026 1 1026 340 1 1026 1027 1 1027 340 1 1028 340 1 1027 1028 1 1027 986 1 986 1028 1
		 986 350 1 350 1028 1 1029 986 1 1027 1029 1 1026 1029 1 991 1029 1 1023 991 1 1021 1014 1
		 1014 1023 1 1025 339 1 1018 1014 1 337 333 1 1015 323 1 323 1013 1 1030 1013 1 323 1030 1
		 1031 1030 1 323 1031 1 1031 1032 1 1032 1030 1 1032 1033 1 1033 1030 1 1032 1034 1
		 1034 1033 1 1035 1033 1 1034 1035 1 1036 1035 1 1034 1036 1 1034 1037 1 1037 1036 1
		 1031 1037 1 1034 1031 1 322 1037 1 1031 322 1 322 1038 1 1038 1037 1 1039 1037 1
		 1038 1039 1 1038 1040 1 1040 1039 1 1038 1041 1 1041 1040 1 313 1040 1 1041 313 1
		 283 1039 1 1040 283 1 1040 312 1 312 283 1 283 1037 1 322 1041 1 322 1042 1 1042 1041 1
		 315 1041 1 1042 315 1 281 1036 1 1037 281 1 281 1043 1 1043 1036 1 1043 1035 1 1043 1044 1
		 1044 1035 1 1045 1035 1 1044 1045 1 1046 1045 1 1044 1046 1 1044 1047 1 1047 1046 1
		 1047 1048 1 1048 1046 1 1048 1049 1 1049 1046 1 1049 1050 1 1050 1046 1 1051 1046 1
		 1050 1051 1 1050 1052 1 1052 1051 1 1053 1051 1 1052 1053 1 1052 1005 1 1005 1053 1
		 1052 1054 1 1054 1005 1 1054 973 1 973 1005 1 1054 1055 1 1055 973 1 1054 1056 1
		 1056 1055 1 1056 972 1 972 1055 1 1054 1057 1 1057 1056 1 1057 1058 1 1058 1056 1
		 1058 971 1 971 1056 1 1058 963 1 963 971 1 1057 1059 1;
	setAttr ".ed[2490:2655]" 1059 1058 1 1059 1060 1 1060 1058 1 1060 962 1 962 1058 1
		 1059 951 1 951 1060 1 951 960 1 960 1060 1 1061 951 1 1059 1061 1 1062 1061 1 1059 1062 1
		 1063 1061 1 1062 1063 1 1048 1063 1 1062 1048 1 1064 1063 1 1048 1064 1 1065 1064 1
		 1048 1065 1 1048 1066 1 1066 1065 1 1066 1067 1 1067 1065 1 1067 1068 1 1068 1065 1
		 1068 1069 1 1069 1065 1 1069 1070 1 1070 1065 1 1069 1071 1 1071 1070 1 1071 1072 1
		 1072 1070 1 1072 1064 1 1064 1070 1 1071 1073 1 1073 1072 1 1073 1063 1 1063 1072 1
		 1071 1074 1 1074 1073 1 1061 1073 1 1074 1061 1 1074 947 1 947 1061 1 947 950 1 950 1061 1
		 942 947 1 1074 942 1 1071 1075 1 1075 1074 1 1075 1076 1 1076 1074 1 1076 941 1 941 1074 1
		 935 941 1 1076 935 1 1077 1076 1 1075 1077 1 1075 1078 1 1078 1077 1 1078 249 1 249 1077 1
		 1077 930 1 930 1076 1 1071 1078 1 1069 1078 1 1068 1078 1 253 1078 1 1068 253 1 1067 253 1
		 279 253 1 1067 279 1 279 1079 1 1079 253 1 1066 279 1 1066 1080 1 1080 279 1 1066 1047 1
		 1047 1080 1 1057 1062 1 1049 1062 1 1057 1049 1 1054 1049 1 1052 1049 1 1081 1051 1
		 1053 1081 1 1053 1012 1 1012 1081 1 1081 1082 1 1082 1051 1 1082 1083 1 1083 1051 1
		 1082 1033 1 1033 1083 1 1081 1084 1 1084 1082 1 1084 1030 1 1030 1082 1 1013 1084 1
		 1081 1013 1 1083 1046 1 1044 1080 1 1083 1045 1 1083 1035 1 1043 1080 1 280 1080 1
		 1043 280 1 992 1023 1 1053 1011 1 1003 1010 1 973 1004 1 973 1002 1 994 999 1 988 1029 1
		 981 987 1 985 350 1 980 1085 1 1085 982 1 980 1086 1 1086 1085 1 1087 1085 1 1086 1087 1
		 1086 979 1 979 1087 1 1088 1087 1 979 1088 1 975 1088 1 979 975 1 1089 1088 1 975 1089 1
		 975 1090 1 1090 1089 1 1090 1091 1 1091 1089 1 1091 1092 1 1092 1089 1 1093 1089 1
		 1092 1093 1 1092 1094 1 1094 1093 1 1092 1095 1 1095 1094 1 1096 1094 1 1095 1096 1
		 1095 1097 1 1097 1096 1 1098 1096 1 1097 1098 1 1097 1099 1 1099 1098 1 1100 1099 1
		 1097 1100 1 1100 1101 1 1101 1099 1 1101 1102 1 1102 1099 1 1102 1103 1 1103 1099 1
		 1104 1099 1 1103 1104 1 1103 1105 1 1105 1104 1 1105 1106 1;
	setAttr ".ed[2656:2821]" 1106 1104 1 1107 1104 1 1106 1107 1 1106 1108 1 1108 1107 1
		 658 1108 1 1106 658 1 650 1107 1 1108 650 1 1109 1107 1 650 1109 1 1109 1098 1 1098 1107 1
		 1098 1104 1 1105 659 1 659 1106 1 1105 1110 1 1110 659 1 1105 1111 1 1111 1110 1
		 1105 1112 1 1112 1111 1 957 1111 1 1112 957 1 1112 1113 1 1113 957 1 1112 1114 1
		 1114 1113 1 1115 1114 1 1112 1115 1 1102 1114 1 1115 1102 1 966 1114 1 1102 966 1
		 1114 964 1 964 1113 1 1105 1115 1 957 1110 1 957 1116 1 1116 1110 1 1116 664 1 664 1110 1
		 1116 940 1 940 664 1 1116 956 1 956 940 1 1103 1115 1 1101 966 1 1117 966 1 1101 1117 1
		 1100 1117 1 1100 1095 1 1095 1117 1 967 1117 1 1095 967 1 1095 1091 1 1091 967 1
		 1109 1096 1 1109 1118 1 1118 1096 1 648 1118 1 1109 648 1 1118 1094 1 1119 1094 1
		 1118 1119 1 1120 1119 1 1118 1120 1 1121 1120 1 1118 1121 1 1118 646 1 646 1121 1
		 1122 1120 1 1121 1122 1 1123 1122 1 1121 1123 1 1124 1123 1 1121 1124 1 1121 644 1
		 644 1124 1 1125 1124 1 644 1125 1 1126 1124 1 1125 1126 1 1125 1127 1 1127 1126 1
		 1125 1128 1 1128 1127 1 1128 1129 1 1129 1127 1 1130 1127 1 1129 1130 1 1129 1131 1
		 1131 1130 1 1129 1132 1 1132 1131 1 1133 1131 1 1132 1133 1 1128 1133 1 1132 1128 1
		 1128 1134 1 1134 1133 1 1134 1135 1 1135 1133 1 1135 1136 1 1136 1133 1 1137 1133 1
		 1136 1137 1 1136 1138 1 1138 1137 1 1139 1137 1 1138 1139 1 1138 1140 1 1140 1139 1
		 1141 1140 1 1138 1141 1 1138 1142 1 1142 1141 1 1138 1143 1 1143 1142 1 1143 1144 1
		 1144 1142 1 1143 1145 1 1145 1144 1 1145 1146 1 1146 1144 1 1147 1144 1 1146 1147 1
		 1146 1148 1 1148 1147 1 1146 1149 1 1149 1148 1 1149 1150 1 1150 1148 1 1151 1148 1
		 1150 1151 1 625 1151 1 1150 625 1 1152 625 1 1150 1152 1 1153 1151 1 625 1153 1 1154 1151 1
		 1153 1154 1 1153 616 1 616 1154 1 1154 1148 1 1154 1155 1 1155 1148 1 1155 1156 1
		 1156 1148 1 1156 1157 1 1157 1148 1 1158 1157 1 1156 1158 1 1156 1159 1 1159 1158 1
		 1160 1158 1 1159 1160 1 1159 1161 1 1161 1160 1 1161 1162 1 1162 1160 1 1161 593 1
		 593 1162 1 593 1163 1 1163 1162 1;
	setAttr ".ed[2822:2987]" 593 589 1 589 1163 1 589 1164 1 1164 1163 1 1165 1163 1
		 1164 1165 1 1166 1165 1 1164 1166 1 1167 1166 1 1164 1167 1 1164 1168 1 1168 1167 1
		 1168 583 1 583 1167 1 1164 1169 1 1169 1168 1 1169 586 1 586 1168 1 1167 1170 1 1170 1166 1
		 1167 581 1 581 1170 1 1170 1171 1 1171 1166 1 1171 1172 1 1172 1166 1 1171 1173 1
		 1173 1172 1 1173 1174 1 1174 1172 1 1174 1162 1 1162 1172 1 1165 1172 1 1162 1165 1
		 1175 1162 1 1174 1175 1 1174 1176 1 1176 1175 1 1176 1177 1 1177 1175 1 1177 1178 1
		 1178 1175 1 1178 1179 1 1179 1175 1 1178 1180 1 1180 1179 1 1178 1181 1 1181 1180 1
		 1181 1158 1 1158 1180 1 1181 1182 1 1182 1158 1 1181 1183 1 1183 1182 1 1183 1157 1
		 1157 1182 1 1183 1147 1 1147 1157 1 1183 1184 1 1184 1147 1 1185 1184 1 1183 1185 1
		 1186 1185 1 1183 1186 1 1186 1187 1 1187 1185 1 1186 1188 1 1188 1187 1 1189 1188 1
		 1186 1189 1 1186 1181 1 1181 1189 1 1190 1189 1 1181 1190 1 1190 1191 1 1191 1189 1
		 1192 1191 1 1190 1192 1 1193 1192 1 1190 1193 1 1190 1178 1 1178 1193 1 1193 1194 1
		 1194 1192 1 1195 1192 1 1194 1195 1 1194 1196 1 1196 1195 1 1197 1195 1 1196 1197 1
		 1196 1198 1 1198 1197 1 1196 1199 1 1199 1198 1 1199 1200 1 1200 1198 1 1201 1198 1
		 1200 1201 1 1200 1202 1 1202 1201 1 1202 1203 1 1203 1201 1 1204 1201 1 1203 1204 1
		 1205 1204 1 1203 1205 1 1203 1206 1 1206 1205 1 1206 1207 1 1207 1205 1 1207 1208 1
		 1208 1205 1 1209 1205 1 1208 1209 1 1210 1209 1 1208 1210 1 1208 1211 1 1211 1210 1
		 1208 1212 1 1212 1211 1 1212 1213 1 1213 1211 1 1213 1214 1 1214 1211 1 1215 1214 1
		 1213 1215 1 1216 1215 1 1213 1216 1 1217 1215 1 1216 1217 1 1216 560 1 560 1217 1
		 1218 1217 1 560 1218 1 1219 1217 1 1218 1219 1 1218 531 1 531 1219 1 1220 1219 1
		 531 1220 1 531 1221 1 1221 1220 1 1221 1222 1 1222 1220 1 1223 1220 1 1222 1223 1
		 1222 1224 1 1224 1223 1 1225 1223 1 1224 1225 1 1224 1226 1 1226 1225 1 1224 1227 1
		 1227 1226 1 1227 1228 1 1228 1226 1 1229 1226 1 1228 1229 1 1230 1229 1 1228 1230 1
		 1231 1230 1 1228 1231 1 1232 1231 1 1228 1232 1 1233 1232 1 1228 1233 1;
	setAttr ".ed[2988:3153]" 1234 1232 1 1233 1234 1 1235 1234 1 1233 1235 1 1233 1236 1
		 1236 1235 1 1233 1227 1 1227 1236 1 1227 1222 1 1222 1236 1 528 1236 1 1222 528 1
		 1222 1237 1 1237 528 1 1236 525 1 525 1235 1 1235 1238 1 1238 1234 1 1235 524 1 524 1238 1
		 524 1239 1 1239 1238 1 1240 1238 1 1239 1240 1 1239 1241 1 1241 1240 1 1241 1242 1
		 1242 1240 1 1243 1240 1 1242 1243 1 1244 1243 1 1242 1244 1 1245 1244 1 1242 1245 1
		 1246 1245 1 1242 1246 1 1242 1247 1 1247 1246 1 1248 1246 1 1247 1248 1 1247 1249 1
		 1249 1248 1 1249 432 1 432 1248 1 1248 431 1 431 1246 1 431 1250 1 1250 1246 1 1251 1246 1
		 1250 1251 1 1252 1251 1 1250 1252 1 1253 1252 1 1250 1253 1 1253 1254 1 1254 1252 1
		 1254 1255 1 1255 1252 1 1255 1256 1 1256 1252 1 1257 1256 1 1255 1257 1 1258 1257 1
		 1255 1258 1 1259 1257 1 1258 1259 1 425 1259 1 1258 425 1 1260 1257 1 1259 1260 1
		 1259 1261 1 1261 1260 1 1262 1261 1 1259 1262 1 423 1262 1 1259 423 1 423 1263 1
		 1263 1262 1 1263 1264 1 1264 1262 1 1263 422 1 422 1264 1 1265 1264 1 422 1265 1
		 1266 1264 1 1265 1266 1 1265 1267 1 1267 1266 1 1267 1268 1 1268 1266 1 1269 1266 1
		 1268 1269 1 1270 1269 1 1268 1270 1 1271 1270 1 1268 1271 1 1268 1272 1 1272 1271 1
		 1273 1271 1 1272 1273 1 1272 1274 1 1274 1273 1 1274 1275 1 1275 1273 1 1275 1276 1
		 1276 1273 1 1277 1276 1 1275 1277 1 1275 1278 1 1278 1277 1 1279 1277 1 1278 1279 1
		 1280 1279 1 1278 1280 1 1281 1280 1 1278 1281 1 1282 1281 1 1278 1282 1 1278 1283 1
		 1283 1282 1 1284 1282 1 1283 1284 1 1283 1285 1 1285 1284 1 1286 1284 1 1285 1286 1
		 1287 1286 1 1285 1287 1 1288 1287 1 1285 1288 1 1285 1289 1 1289 1288 1 1289 1290 1
		 1290 1288 1 1290 1291 1 1291 1288 1 1290 1292 1 1292 1291 1 1293 1291 1 1292 1293 1
		 1272 1293 1 1292 1272 1 1267 1291 1 1293 1267 1 1294 1291 1 1267 1294 1 1294 1295 1
		 1295 1291 1 1296 1291 1 1295 1296 1 1297 1296 1 1295 1297 1 1298 1297 1 1295 1298 1
		 1299 1298 1 1295 1299 1 1299 1300 1 1300 1298 1 1265 1300 1 1299 1265 1 1299 1294 1
		 1294 1265 1 420 1300 1 1265 420 1 420 413 1 413 1300 1;
	setAttr ".ed[3154:3319]" 1300 411 1 411 1298 1 411 1297 1 411 1301 1 1301 1297 1
		 1301 1302 1 1302 1297 1 1303 1302 1 1301 1303 1 1301 1304 1 1304 1303 1 1304 1305 1
		 1305 1303 1 1304 408 1 408 1305 1 1306 1305 1 408 1306 1 408 1307 1 1307 1306 1 1307 1308 1
		 1308 1306 1 1308 1309 1 1309 1306 1 1310 1306 1 1309 1310 1 1309 1311 1 1311 1310 1
		 1311 1312 1 1312 1310 1 1313 1310 1 1312 1313 1 1314 1313 1 1312 1314 1 1314 1315 1
		 1315 1313 1 1316 1313 1 1315 1316 1 1315 1317 1 1317 1316 1 1318 1316 1 1317 1318 1
		 1319 1318 1 1317 1319 1 1320 1319 1 1317 1320 1 1321 1320 1 1317 1321 1 1321 1322 1
		 1322 1320 1 1323 1322 1 1321 1323 1 1324 1323 1 1321 1324 1 1321 1314 1 1314 1324 1
		 1314 1325 1 1325 1324 1 1325 1326 1 1326 1324 1 1326 1327 1 1327 1324 1 1328 1324 1
		 1327 1328 1 1329 1328 1 1327 1329 1 1330 1329 1 1327 1330 1 1330 1331 1 1331 1329 1
		 1332 1329 1 1331 1332 1 1333 1332 1 1331 1333 1 1334 1333 1 1331 1334 1 1335 1334 1
		 1331 1335 1 1336 1334 1 1335 1336 1 1335 373 1 373 1336 1 1337 1336 1 373 1337 1
		 373 1338 1 1338 1337 1 1338 1339 1 1339 1337 1 1339 1340 1 1340 1337 1 1341 1340 1
		 1339 1341 1 1339 1342 1 1342 1341 1 1342 1343 1 1343 1341 1 1342 1344 1 1344 1343 1
		 1344 1345 1 1345 1343 1 1345 1346 1 1346 1343 1 1345 1347 1 1347 1346 1 1347 1348 1
		 1348 1346 1 1347 1349 1 1349 1348 1 1349 1350 1 1350 1348 1 1350 1351 1 1351 1348 1
		 1351 1352 1 1352 1348 1 1352 1336 1 1336 1348 1 1352 1353 1 1353 1336 1 1352 1354 1
		 1354 1353 1 1354 1333 1 1333 1353 1 1355 1333 1 1354 1355 1 1354 1356 1 1356 1355 1
		 1356 1322 1 1322 1355 1 1322 1332 1 1332 1355 1 1357 1356 1 1354 1357 1 1358 1357 1
		 1354 1358 1 1354 1359 1 1359 1358 1 1359 1360 1 1360 1358 1 1360 1361 1 1361 1358 1
		 1360 1362 1 1362 1361 1 1363 1361 1 1362 1363 1 1364 1363 1 1362 1364 1 1365 1364 1
		 1362 1365 1 1362 1366 1 1366 1365 1 1366 1367 1 1367 1365 1 1366 1360 1 1360 1367 1
		 1368 1365 1 1367 1368 1 1367 1359 1 1359 1368 1 1359 1369 1 1369 1368 1 1370 1369 1
		 1359 1370 1 1351 1369 1 1370 1351 1 1351 1371 1 1371 1369 1 1371 1372 1;
	setAttr ".ed[3320:3485]" 1372 1369 1 1373 1372 1 1371 1373 1 1374 1373 1 1371 1374 1
		 1374 1375 1 1375 1373 1 1374 1376 1 1376 1375 1 1377 1375 1 1376 1377 1 1376 1378 1
		 1378 1377 1 1378 1379 1 1379 1377 1 1379 1380 1 1380 1377 1 1381 1380 1 1379 1381 1
		 1379 1382 1 1382 1381 1 1382 1383 1 1383 1381 1 1383 1384 1 1384 1381 1 1384 1385 1
		 1385 1381 1 1385 1386 1 1386 1381 1 1385 1387 1 1387 1386 1 1387 1388 1 1388 1386 1
		 1389 1386 1 1388 1389 1 1388 1390 1 1390 1389 1 1390 1391 1 1391 1389 1 1392 1389 1
		 1391 1392 1 1391 1393 1 1393 1392 1 1393 1394 1 1394 1392 1 1395 1392 1 1394 1395 1
		 1394 1396 1 1396 1395 1 1396 1397 1 1397 1395 1 1396 1365 1 1365 1397 1 1397 1398 1
		 1398 1395 1 1397 1372 1 1372 1398 1 1375 1398 1 1372 1375 1 1375 1380 1 1380 1398 1
		 1380 1392 1 1392 1398 1 1368 1372 1 1397 1368 1 1394 1399 1 1399 1396 1 1399 1400 1
		 1400 1396 1 1400 1364 1 1364 1396 1 1400 1401 1 1401 1364 1 1400 1402 1 1402 1401 1
		 1402 1403 1 1403 1401 1 1403 1404 1 1404 1401 1 1403 1405 1 1405 1404 1 1405 1406 1
		 1406 1404 1 1406 1407 1 1407 1404 1 1363 1404 1 1407 1363 1 1406 1408 1 1408 1407 1
		 1408 1409 1 1409 1407 1 1408 1410 1 1410 1409 1 1411 1409 1 1410 1411 1 1410 1412 1
		 1412 1411 1 1410 1413 1 1413 1412 1 1413 1414 1 1414 1412 1 1413 1415 1 1415 1414 1
		 1416 1414 1 1415 1416 1 1415 1417 1 1417 1416 1 1417 1316 1 1316 1416 1 1415 1418 1
		 1418 1417 1 1418 1419 1 1419 1417 1 1418 1420 1 1420 1419 1 1420 1421 1 1421 1419 1
		 1420 1422 1 1422 1421 1 1422 1423 1 1423 1421 1 1424 1421 1 1423 1424 1 1425 1424 1
		 1423 1425 1 1426 1425 1 1423 1426 1 1427 1425 1 1426 1427 1 1428 1427 1 1426 1428 1
		 1429 1428 1 1426 1429 1 1422 1429 1 1426 1422 1 1429 1430 1 1430 1428 1 1430 1431 1
		 1431 1428 1 1431 1432 1 1432 1428 1 1432 1287 1 1287 1428 1 1433 1432 1 1431 1433 1
		 1434 1432 1 1433 1434 1 1433 1435 1 1435 1434 1 1433 1430 1 1430 1435 1 1436 1435 1
		 1430 1436 1 1430 1420 1 1420 1436 1 1418 1435 1 1436 1418 1 1437 1434 1 1435 1437 1
		 1435 1415 1 1415 1437 1 1415 1438 1 1438 1437 1 1410 1437 1 1438 1410 1 1437 1439 1;
	setAttr ".ed[3486:3651]" 1439 1434 1 1439 1286 1 1286 1434 1 1439 1440 1 1440 1286 1
		 1441 1440 1 1439 1441 1 1439 1442 1 1442 1441 1 1442 1443 1 1443 1441 1 1443 1444 1
		 1444 1441 1 1445 1444 1 1443 1445 1 1443 1446 1 1446 1445 1 1446 1447 1 1447 1445 1
		 1447 1448 1 1448 1445 1 1447 1449 1 1449 1448 1 1449 1450 1 1450 1448 1 1280 1448 1
		 1450 1280 1 1450 1451 1 1451 1280 1 1451 1452 1 1452 1280 1 1451 1453 1 1453 1452 1
		 1453 1454 1 1454 1452 1 1454 1277 1 1277 1452 1 1453 1455 1 1455 1454 1 1455 1456 1
		 1456 1454 1 1455 1457 1 1457 1456 1 1457 1458 1 1458 1456 1 1458 1459 1 1459 1456 1
		 1459 1460 1 1460 1456 1 1459 1461 1 1461 1460 1 1461 1462 1 1462 1460 1 1461 1463 1
		 1463 1462 1 1463 1464 1 1464 1462 1 1464 1465 1 1465 1462 1 1464 1466 1 1466 1465 1
		 1466 1467 1 1467 1465 1 1468 1467 1 1466 1468 1 1469 1468 1 1466 1469 1 1470 1469 1
		 1466 1470 1 1466 1471 1 1471 1470 1 1471 1472 1 1472 1470 1 1472 1473 1 1473 1470 1
		 1473 1474 1 1474 1470 1 1473 1475 1 1475 1474 1 1473 1476 1 1476 1475 1 1476 1477 1
		 1477 1475 1 1477 1478 1 1478 1475 1 1479 1475 1 1478 1479 1 1478 1257 1 1257 1479 1
		 1477 1251 1 1251 1478 1 1251 1256 1 1256 1478 1 1477 1245 1 1245 1251 1 1477 1480 1
		 1480 1245 1 1480 1481 1 1481 1245 1 1480 1482 1 1482 1481 1 1243 1481 1 1482 1243 1
		 1482 1234 1 1234 1243 1 1480 1231 1 1231 1482 1 1480 1483 1 1483 1231 1 1477 1483 1
		 1476 1483 1 1484 1483 1 1476 1484 1 1476 1472 1 1472 1484 1 1472 1485 1 1485 1484 1
		 1485 1486 1 1486 1484 1 1485 1487 1 1487 1486 1 1487 1229 1 1229 1486 1 1488 1229 1
		 1487 1488 1 1487 1489 1 1489 1488 1 1490 1488 1 1489 1490 1 1489 1491 1 1491 1490 1
		 1491 1472 1 1472 1490 1 1472 1492 1 1492 1490 1 1492 1493 1 1493 1490 1 1493 1494 1
		 1494 1490 1 1495 1494 1 1493 1495 1 1496 1495 1 1493 1496 1 1496 1497 1 1497 1495 1
		 1497 1471 1 1471 1495 1 1464 1495 1 1471 1464 1 1464 1498 1 1498 1495 1 1498 1499 1
		 1499 1495 1 1499 1500 1 1500 1495 1 1499 1219 1 1219 1500 1 1501 1500 1 1219 1501 1
		 1501 1225 1 1225 1500 1 1225 1488 1 1488 1500 1 1494 1500 1 1488 1494 1 1214 1219 1;
	setAttr ".ed[3652:3817]" 1499 1214 1 1499 1502 1 1502 1214 1 1503 1502 1 1499 1503 1
		 1503 1504 1 1504 1502 1 1503 1505 1 1505 1504 1 1506 1505 1 1503 1506 1 1507 1506 1
		 1503 1507 1 1503 1508 1 1508 1507 1 1503 1498 1 1498 1508 1 1498 1463 1 1463 1508 1
		 1508 1461 1 1461 1507 1 1461 1506 1 1458 1505 1 1506 1458 1 1458 1504 1 1458 1509 1
		 1509 1504 1 1509 1510 1 1510 1504 1 1511 1510 1 1509 1511 1 1512 1511 1 1509 1512 1
		 1509 1457 1 1457 1512 1 1457 1513 1 1513 1512 1 1513 1514 1 1514 1512 1 1515 1514 1
		 1513 1515 1 1513 1516 1 1516 1515 1 1516 1517 1 1517 1515 1 1516 1451 1 1451 1517 1
		 1513 1455 1 1455 1516 1 1517 1514 1 1450 1514 1 1517 1450 1 1514 1518 1 1518 1512 1
		 1518 1519 1 1519 1512 1 1518 1520 1 1520 1519 1 1520 1521 1 1521 1519 1 1520 1522 1
		 1522 1521 1 1520 1523 1 1523 1522 1 1523 1524 1 1524 1522 1 1523 1525 1 1525 1524 1
		 1525 1526 1 1526 1524 1 1526 1527 1 1527 1524 1 1526 1528 1 1528 1527 1 1529 1528 1
		 1526 1529 1 1526 1530 1 1530 1529 1 1530 1192 1 1192 1529 1 1531 1530 1 1526 1531 1
		 1531 1532 1 1532 1530 1 1532 1191 1 1191 1530 1 1532 1533 1 1533 1191 1 1533 1534 1
		 1534 1191 1 1533 1188 1 1188 1534 1 1533 1535 1 1535 1188 1 1536 1188 1 1535 1536 1
		 1537 1536 1 1535 1537 1 1538 1537 1 1535 1538 1 1539 1538 1 1535 1539 1 1540 1539 1
		 1535 1540 1 1541 1539 1 1540 1541 1 1542 1541 1 1540 1542 1 1540 1532 1 1532 1542 1
		 1532 1543 1 1543 1542 1 1543 1544 1 1544 1542 1 1544 1545 1 1545 1542 1 1546 1542 1
		 1545 1546 1 1545 1547 1 1547 1546 1 1545 1548 1 1548 1547 1 1548 1549 1 1549 1547 1
		 1550 1547 1 1549 1550 1 1549 1551 1 1551 1550 1 1551 1552 1 1552 1550 1 1551 1553 1
		 1553 1552 1 1554 1552 1 1553 1554 1 1553 1555 1 1555 1554 1 1555 1556 1 1556 1554 1
		 1557 1554 1 1556 1557 1 1556 1558 1 1558 1557 1 1556 1559 1 1559 1558 1 1560 1558 1
		 1559 1560 1 1559 1561 1 1561 1560 1 1562 1560 1 1561 1562 1 1561 1563 1 1563 1562 1
		 1390 1562 1 1563 1390 1 1561 1399 1 1399 1563 1 1561 1564 1 1564 1399 1 1393 1563 1
		 1399 1393 1 1388 1560 1 1562 1388 1 1559 1564 1 1559 1565 1 1565 1564 1 1565 1402 1;
	setAttr ".ed[3818:3983]" 1402 1564 1 1565 1566 1 1566 1402 1 1566 1567 1 1567 1402 1
		 1566 1568 1 1568 1567 1 1568 1442 1 1442 1567 1 1442 1405 1 1405 1567 1 1568 1569 1
		 1569 1442 1 1570 1569 1 1568 1570 1 1571 1570 1 1568 1571 1 1555 1571 1 1568 1555 1
		 1555 1551 1 1551 1571 1 1571 1549 1 1549 1570 1 1570 1572 1 1572 1569 1 1572 1573 1
		 1573 1569 1 1446 1569 1 1573 1446 1 1572 1574 1 1574 1573 1 1574 1575 1 1575 1573 1
		 1575 1576 1 1576 1573 1 1576 1577 1 1577 1573 1 1577 1447 1 1447 1573 1 1576 1578 1
		 1578 1577 1 1576 1579 1 1579 1578 1 1576 1580 1 1580 1579 1 1581 1579 1 1580 1581 1
		 1544 1581 1 1580 1544 1 1580 1574 1 1574 1544 1 1582 1544 1 1574 1582 1 1581 1525 1
		 1525 1579 1 1531 1525 1 1581 1531 1 1581 1543 1 1543 1531 1 1579 1523 1 1523 1578 1
		 1578 1583 1 1583 1577 1 1583 1449 1 1449 1577 1 1514 1449 1 1583 1514 1 1578 1520 1
		 1520 1583 1 1575 1580 1 1572 1582 1 1572 1584 1 1584 1582 1 1584 1545 1 1545 1582 1
		 1570 1584 1 1548 1584 1 1570 1548 1 1566 1555 1 1565 1555 1 1585 1558 1 1560 1585 1
		 1560 1387 1 1387 1585 1 1387 1586 1 1586 1585 1 1586 1587 1 1587 1585 1 1588 1587 1
		 1586 1588 1 1586 1589 1 1589 1588 1 1586 1590 1 1590 1589 1 1590 1385 1 1385 1589 1
		 1589 1591 1 1591 1588 1 1589 1592 1 1592 1591 1 1592 1593 1 1593 1591 1 1593 1130 1
		 1130 1591 1 1594 1591 1 1130 1594 1 1130 1595 1 1595 1594 1 1596 1594 1 1595 1596 1
		 1597 1596 1 1595 1597 1 1140 1597 1 1595 1140 1 1140 1187 1 1187 1597 1 1536 1597 1
		 1187 1536 1 1536 1598 1 1598 1597 1 1598 1596 1 1598 1599 1 1599 1596 1 1598 1600 1
		 1600 1599 1 1600 1601 1 1601 1599 1 1601 1594 1 1594 1599 1 1601 1588 1 1588 1594 1
		 1600 1602 1 1602 1601 1 1602 1587 1 1587 1601 1 1557 1587 1 1602 1557 1 1603 1557 1
		 1602 1603 1 1604 1603 1 1602 1604 1 1604 1605 1 1605 1603 1 1605 1552 1 1552 1603 1
		 1537 1605 1 1604 1537 1 1604 1598 1 1598 1537 1 1600 1604 1 1592 1123 1 1123 1593 1
		 1123 1126 1 1126 1593 1 1606 1592 1 1589 1606 1 1589 1384 1 1384 1606 1 1607 1606 1
		 1384 1607 1 1607 1608 1 1608 1606 1 1608 1609 1 1609 1606 1 1608 1610 1 1610 1609 1;
	setAttr ".ed[3984:4149]" 1610 1122 1 1122 1609 1 1122 1592 1 1592 1609 1 1608 1611 1
		 1611 1610 1 1611 1612 1 1612 1610 1 1612 1613 1 1613 1610 1 1614 1613 1 1612 1614 1
		 1615 1614 1 1612 1615 1 1615 1616 1 1616 1614 1 1616 1617 1 1617 1614 1 1616 1618 1
		 1618 1617 1 1618 1619 1 1619 1617 1 1620 1619 1 1618 1620 1 1618 1621 1 1621 1620 1
		 1618 1622 1 1622 1621 1 1622 1623 1 1623 1621 1 1624 1621 1 1623 1624 1 1623 1625 1
		 1625 1624 1 1623 1626 1 1626 1625 1 1626 1627 1 1627 1625 1 1628 1627 1 1626 1628 1
		 1626 1629 1 1629 1628 1 1630 1628 1 1629 1630 1 1629 1631 1 1631 1630 1 1632 1630 1
		 1631 1632 1 1631 1633 1 1633 1632 1 1634 1632 1 1633 1634 1 1633 364 1 364 1634 1
		 1633 1635 1 1635 364 1 1636 1632 1 1634 1636 1 1634 358 1 358 1636 1 363 358 1 1634 363 1
		 1636 1637 1 1637 1632 1 1638 1637 1 1636 1638 1 1636 1627 1 1627 1638 1 1636 357 1
		 357 1627 1 1638 1630 1 1630 1637 1 1631 1635 1 1631 1639 1 1639 1635 1 1639 1640 1
		 1640 1635 1 1640 1641 1 1641 1635 1 1641 367 1 367 1635 1 1641 1642 1 1642 367 1
		 1642 1338 1 1338 367 1 1338 371 1 371 367 1 1642 1342 1 1342 1338 1 1641 1342 1 1643 1342 1
		 1641 1643 1 1644 1643 1 1641 1644 1 1645 1644 1 1641 1645 1 1645 1646 1 1646 1644 1
		 1645 1647 1 1647 1646 1 1639 1647 1 1645 1639 1 1629 1646 1 1647 1629 1 1629 1648 1
		 1648 1646 1 1648 1649 1 1649 1646 1 1643 1646 1 1649 1643 1 1649 1344 1 1344 1643 1
		 1649 1347 1 1347 1344 1 1649 1650 1 1650 1347 1 1650 1651 1 1651 1347 1 1650 1652 1
		 1652 1651 1 1652 1349 1 1349 1651 1 1650 1653 1 1653 1652 1 1653 1654 1 1654 1652 1
		 1654 1655 1 1655 1652 1 1654 1656 1 1656 1655 1 1656 1657 1 1657 1655 1 1656 1658 1
		 1658 1657 1 1656 1659 1 1659 1658 1 1660 1658 1 1659 1660 1 1661 1660 1 1659 1661 1
		 1661 1662 1 1662 1660 1 1661 1663 1 1663 1662 1 1661 1664 1 1664 1663 1 1665 1663 1
		 1664 1665 1 1664 1653 1 1653 1665 1 1653 1666 1 1666 1665 1 1666 1667 1 1667 1665 1
		 1668 1667 1 1666 1668 1 1669 1667 1 1668 1669 1 1668 1649 1 1649 1669 1 1669 1670 1
		 1670 1667 1 1670 1671 1 1671 1667 1 1671 1662 1 1662 1667 1;
	setAttr ".ed[4150:4315]" 1671 1672 1 1672 1662 1 1673 1672 1 1671 1673 1 1674 1673 1
		 1671 1674 1 1675 1673 1 1674 1675 1 1674 1676 1 1676 1675 1 1674 1670 1 1670 1676 1
		 1677 1676 1 1670 1677 1 1670 1623 1 1623 1677 1 1677 1622 1 1622 1676 1 1678 1676 1
		 1622 1678 1 1679 1676 1 1678 1679 1 1615 1679 1 1678 1615 1 1615 1680 1 1680 1679 1
		 1680 1660 1 1660 1679 1 1672 1679 1 1660 1672 1 1675 1679 1 1672 1675 1 1615 1611 1
		 1611 1680 1 1658 1680 1 1611 1658 1 1669 1623 1 1669 1648 1 1648 1623 1 1653 1668 1
		 1667 1663 1 1661 1654 1 1654 1664 1 1656 1661 1 1681 1657 1 1658 1681 1 1608 1681 1
		 1658 1608 1 1681 1682 1 1682 1657 1 1376 1657 1 1682 1376 1 1376 1683 1 1683 1657 1
		 1681 1684 1 1684 1682 1 1684 1378 1 1378 1682 1 1684 1685 1 1685 1378 1 1685 1382 1
		 1382 1378 1 1685 1607 1 1607 1382 1 1684 1607 1 1681 1607 1 1683 1655 1 1683 1686 1
		 1686 1655 1 1683 1350 1 1350 1686 1 1652 1686 1 1350 1652 1 1683 1374 1 1374 1350 1
		 1650 1668 1 1640 1645 1 1631 1647 1 1638 1628 1 1626 1648 1 357 1625 1 357 1687 1
		 1687 1625 1 357 1085 1 1085 1687 1 1085 1688 1 1688 1687 1 1688 1689 1 1689 1687 1
		 1690 1689 1 1688 1690 1 1688 1087 1 1087 1690 1 1620 1689 1 1690 1620 1 1689 1625 1
		 1689 1624 1 1689 1621 1 1618 1678 1 1690 1619 1 1690 1088 1 1088 1619 1 1088 1691 1
		 1691 1619 1 1691 1617 1 1691 1692 1 1692 1617 1 1693 1617 1 1692 1693 1 1692 1093 1
		 1093 1693 1 1119 1693 1 1093 1119 1 1119 1613 1 1613 1693 1 1613 1617 1 1691 1093 1
		 1616 1678 1 1119 1610 1 1387 1590 1 1587 1558 1 1556 1565 1 1603 1554 1 1605 1550 1
		 1605 1538 1 1538 1550 1 1550 1539 1 1539 1547 1 1541 1546 1 1547 1541 1 1533 1540 1
		 1694 1528 1 1529 1694 1 1529 1195 1 1195 1694 1 1695 1528 1 1694 1695 1 1694 1204 1
		 1204 1695 1 1209 1695 1 1204 1209 1 1521 1695 1 1209 1521 1 1510 1521 1 1209 1510 1
		 1521 1527 1 1527 1695 1 1527 1522 1 1510 1519 1 1518 1583 1 1519 1511 1 1510 1502 1
		 1510 1210 1 1210 1502 1 1210 1214 1 1497 1696 1 1696 1471 1 1496 1696 1 1492 1696 1
		 1496 1492 1 1472 1696 1 1487 1491 1 1485 1491 1 1229 1484 1 1229 1483 1 1479 1474 1;
	setAttr ".ed[4316:4481]" 1479 1468 1 1468 1474 1 1479 1697 1 1697 1468 1 1697 1698 1
		 1698 1468 1 1699 1698 1 1697 1699 1 1697 1261 1 1261 1699 1 1261 1264 1 1264 1699 1
		 1266 1698 1 1699 1266 1 1479 1260 1 1260 1697 1 1474 1469 1 1698 1467 1 1269 1467 1
		 1698 1269 1 1269 1465 1 1465 1270 1 1270 1462 1 1700 1462 1 1270 1700 1 1701 1700 1
		 1270 1701 1 1701 1273 1 1273 1700 1 1700 1460 1 1459 1506 1 1700 1456 1 1700 1276 1
		 1276 1456 1 1276 1454 1 1453 1516 1 1448 1281 1 1281 1445 1 1702 1445 1 1281 1702 1
		 1443 1569 1 1702 1444 1 1440 1444 1 1702 1440 1 1702 1284 1 1284 1440 1 1439 1406 1
		 1406 1442 1 1437 1406 1 1286 1432 1 1429 1420 1 1428 1288 1 1288 1427 1 1427 1703 1
		 1703 1425 1 1302 1425 1 1703 1302 1 1305 1425 1 1302 1305 1 1305 1704 1 1704 1425 1
		 1427 1296 1 1296 1703 1 1704 1424 1 1705 1424 1 1704 1705 1 1704 1313 1 1313 1705 1
		 1419 1705 1 1313 1419 1 1705 1421 1 1313 1417 1 1318 1414 1 1416 1318 1 1413 1438 1
		 1318 1412 1 1706 1411 1 1412 1706 1 1319 1706 1 1412 1319 1 1706 1409 1 1707 1409 1
		 1706 1707 1 1706 1357 1 1357 1707 1 1361 1707 1 1357 1361 1 1361 1407 1 1407 1707 1
		 1408 1437 1 1403 1567 1 1363 1401 1 1400 1564 1 1391 1563 1 1380 1389 1 1380 1386 1
		 1383 1607 1 1351 1374 1 1354 1370 1 1706 1356 1 1706 1320 1 1320 1356 1 1352 1370 1
		 1340 1348 1 1336 1340 1 1340 1343 1 1343 1348 1 1353 1334 1 1332 1323 1 1323 1329 1
		 1330 1335 1 375 1335 1 1330 375 1 1330 1708 1 1708 375 1 1330 1709 1 1709 1708 1
		 1709 379 1 379 1708 1 1709 1710 1 1710 379 1 1709 1711 1 1711 1710 1 1711 383 1 383 1710 1
		 1709 1326 1 1326 1711 1 1326 400 1 400 1711 1 1330 1326 1 1323 1328 1 1325 1712 1
		 1712 1326 1 1713 1326 1 1712 1713 1 1712 1714 1 1714 1713 1 1712 1308 1 1308 1714 1
		 1712 1311 1 1311 1308 1 1714 404 1 404 1713 1 1714 407 1 407 404 1 1714 1307 1 1307 407 1
		 1713 403 1 403 1326 1 1325 1311 1 1314 1311 1 1315 1321 1 1704 1310 1 1704 1306 1
		 1703 1297 1 411 1304 1 1427 1291 1 1289 1292 1 1715 1292 1 1289 1715 1 1715 1274 1
		 1274 1292 1 1716 1274 1 1715 1716 1 1283 1716 1 1715 1283 1;
	setAttr ".ed[4482:4647]" 1278 1274 1 1716 1278 1 1285 1715 1 1702 1282 1 1452 1279 1
		 1701 1271 1 1268 1293 1 1254 1258 1 1254 429 1 429 1258 1 1253 429 1 431 1253 1 1242 1249 1
		 1242 1717 1 1717 1249 1 1717 1718 1 1718 1249 1 1718 434 1 434 1249 1 1718 1719 1
		 1719 434 1 1718 1241 1 1241 1719 1 1241 1720 1 1720 1719 1 1720 440 1 440 1719 1
		 518 1720 1 1241 518 1 1721 1720 1 518 1721 1 442 1720 1 1721 442 1 1717 1241 1 1481 1244 1
		 1234 1240 1 1239 519 1 519 1241 1 1482 1232 1 1483 1230 1 1488 1226 1 1501 1223 1
		 1501 1220 1 1221 1237 1 529 1237 1 1221 529 1 1219 1215 1 1212 1216 1 1212 1207 1
		 1207 1216 1 1207 562 1 562 1216 1 1206 563 1 563 1207 1 1203 565 1 565 1206 1 1694 1201 1
		 1694 1197 1 1197 1201 1 1202 565 1 1202 1722 1 1722 565 1 1200 1722 1 1200 1723 1
		 1723 1722 1 1723 1724 1 1724 1722 1 1724 566 1 566 1722 1 1724 1725 1 1725 566 1
		 1724 1170 1 1170 1725 1 579 1725 1 1170 579 1 1171 1724 1 1723 1171 1 1723 1199 1
		 1199 1171 1 1196 1726 1 1726 1199 1 1726 1173 1 1173 1199 1 1726 1176 1 1176 1173 1
		 1726 1727 1 1727 1176 1 1727 1193 1 1193 1176 1 1196 1193 1 1727 1196 1 1534 1189 1
		 1187 1141 1 1141 1185 1 1185 1144 1 1144 1184 1 1158 1179 1 1177 1193 1 1179 1162 1
		 589 1169 1 1179 1160 1 1159 1728 1 1728 1161 1 594 1161 1 1728 594 1 1155 1728 1
		 1159 1155 1 1155 1729 1 1729 1728 1 1730 1728 1 1729 1730 1 1729 615 1 615 1730 1
		 1729 1154 1 1154 615 1 1730 1731 1 1731 1728 1 596 1728 1 1731 596 1 1730 1732 1
		 1732 1731 1 1733 1731 1 1732 1733 1 599 1733 1 1732 599 1 598 1731 1 1733 598 1 1730 610 1
		 610 1732 1 1149 1152 1 1149 1734 1 1734 1152 1 1734 1735 1 1735 1152 1 1735 627 1
		 627 1152 1 1734 1736 1 1736 1735 1 1135 1736 1 1734 1135 1 1736 637 1 637 1735 1
		 1736 1737 1 1737 637 1 1737 642 1 642 637 1 1736 1134 1 1134 1737 1 1145 1734 1 1149 1145 1
		 1136 1734 1 1145 1136 1 1143 1136 1 1185 1142 1 1595 1139 1 1131 1139 1 1595 1131 1
		 1131 1137 1 1128 1737 1 643 1737 1 1128 643 1 1593 1127 1 1125 643 1 1610 1120 1
		 1691 1089 1 1090 967 1;
	setAttr ".ed[4648:4813]" 357 982 1 997 978 1 970 1090 1 963 968 1 969 1090 1
		 961 1113 1 958 1113 1 951 959 1 944 956 1 954 944 1 959 953 1 959 952 1 941 937 1
		 934 939 1 934 669 1 669 939 1 1076 931 1 932 675 1 675 933 1 675 672 1 672 933 1
		 923 1738 1 1738 932 1 1738 676 1 676 932 1 1738 1739 1 1739 676 1 1739 1740 1 1740 676 1
		 1739 1741 1 1741 1740 1 1741 1742 1 1742 1740 1 1741 1743 1 1743 1742 1 1743 1744 1
		 1744 1742 1 1744 1745 1 1745 1742 1 1744 1746 1 1746 1745 1 1746 688 1 688 1745 1
		 688 1747 1 1747 1745 1 1747 1748 1 1748 1745 1 1749 1748 1 1747 1749 1 1747 1750 1
		 1750 1749 1 680 1749 1 1750 680 1 1751 1749 1 680 1751 1 1752 1751 1 680 1752 1 677 1751 1
		 1752 677 1 677 1740 1 1740 1751 1 1740 1748 1 1748 1751 1 1747 684 1 684 1750 1 1744 895 1
		 895 1746 1 895 689 1 689 1746 1 1748 1742 1 1743 1753 1 1753 1744 1 1753 896 1 896 1744 1
		 1743 920 1 920 1753 1 1754 1753 1 920 1754 1 1754 898 1 898 1753 1 1754 919 1 919 898 1
		 919 1755 1 1755 898 1 919 1756 1 1756 1755 1 1756 1757 1 1757 1755 1 903 1755 1 1757 903 1
		 1756 1758 1 1758 1757 1 1758 905 1 905 1757 1 1756 915 1 915 1758 1 1741 920 1 1739 922 1
		 922 1741 1 1738 922 1 1077 929 1 1077 1759 1 1759 929 1 1077 248 1 248 1759 1 1759 928 1
		 1760 928 1 1759 1760 1 1759 1761 1 1761 1760 1 1761 913 1 913 1760 1 913 1762 1 1762 1760 1
		 1759 247 1 247 1761 1 1762 928 1 1762 926 1 1762 914 1 914 926 1 914 925 1 918 1756 1
		 911 1758 1 1761 912 1 1763 912 1 1761 1763 1 1761 245 1 245 1763 1 245 240 1 240 1763 1
		 240 237 1 237 1763 1 909 1763 1 237 909 1 1763 910 1 908 1758 1 193 902 1 900 1755 1
		 901 869 1 869 899 1 869 897 1 868 873 1 863 875 1 190 860 1 864 190 1 859 853 1 859 852 1
		 1764 852 1 859 1764 1 859 187 1 187 1764 1 1765 1764 1 187 1765 1 187 181 1 181 1765 1
		 1766 1765 1 181 1766 1 177 1766 1 181 177 1 1767 1766 1 177 1767 1 1767 851 1 851 1766 1
		 851 1764 1 1764 1766 1 1767 850 1;
	setAttr ".ed[4814:4979]" 1768 850 1 1767 1768 1 1767 1769 1 1769 1768 1 1770 1768 1
		 1769 1770 1 1769 1771 1 1771 1770 1 1769 172 1 172 1771 1 1769 176 1 176 172 1 1772 1770 1
		 1771 1772 1 1771 171 1 171 1772 1 171 1773 1 1773 1772 1 1774 1772 1 1773 1774 1
		 1773 1775 1 1775 1774 1 1775 1776 1 1776 1774 1 1775 1777 1 1777 1776 1 1777 1778 1
		 1778 1776 1 1778 1779 1 1779 1776 1 1779 1772 1 1772 1776 1 1779 1780 1 1780 1772 1
		 1779 1781 1 1781 1780 1 1781 1782 1 1782 1780 1 1782 1770 1 1770 1780 1 1783 1770 1
		 1782 1783 1 1782 1784 1 1784 1783 1 1785 1783 1 1784 1785 1 1786 1785 1 1784 1786 1
		 1787 1786 1 1784 1787 1 1788 1786 1 1787 1788 1 1787 1781 1 1781 1788 1 1781 1789 1
		 1789 1788 1 1790 1788 1 1789 1790 1 1791 1790 1 1789 1791 1 1789 1778 1 1778 1791 1
		 1792 1790 1 1791 1792 1 1793 1792 1 1791 1793 1 1791 1794 1 1794 1793 1 1795 1794 1
		 1791 1795 1 1796 1795 1 1791 1796 1 1791 1777 1 1777 1796 1 1797 1796 1 1777 1797 1
		 1777 1798 1 1798 1797 1 1798 1799 1 1799 1797 1 1799 1800 1 1800 1797 1 1800 1801 1
		 1801 1797 1 1802 1801 1 1800 1802 1 1800 1803 1 1803 1802 1 1804 1802 1 1803 1804 1
		 1803 1805 1 1805 1804 1 1805 1806 1 1806 1804 1 1806 1807 1 1807 1804 1 1806 1808 1
		 1808 1807 1 1806 1809 1 1809 1808 1 1809 1810 1 1810 1808 1 1811 1808 1 1810 1811 1
		 1810 1812 1 1812 1811 1 1813 1812 1 1810 1813 1 1814 1813 1 1810 1814 1 1815 1813 1
		 1814 1815 1 1814 1816 1 1816 1815 1 1816 1817 1 1817 1815 1 1817 1818 1 1818 1815 1
		 1817 1819 1 1819 1818 1 1819 1820 1 1820 1818 1 1820 1821 1 1821 1818 1 1822 1818 1
		 1821 1822 1 1821 1823 1 1823 1822 1 1824 1822 1 1823 1824 1 1812 1824 1 1823 1812 1
		 1823 1825 1 1825 1812 1 1823 1826 1 1826 1825 1 1827 1825 1 1826 1827 1 1828 1827 1
		 1826 1828 1 1826 1829 1 1829 1828 1 1829 1830 1 1830 1828 1 1830 1831 1 1831 1828 1
		 1830 1832 1 1832 1831 1 1832 1833 1 1833 1831 1 1833 1834 1 1834 1831 1 1833 1811 1
		 1811 1834 1 1811 1828 1 1828 1834 1 1835 1811 1 1833 1835 1 1833 1836 1 1836 1835 1
		 1837 1835 1 1836 1837 1 1836 1838 1 1838 1837 1 1836 1839 1 1839 1838 1;
	setAttr ".ed[4980:5145]" 1840 1839 1 1836 1840 1 1836 1832 1 1832 1840 1 1832 1841 1
		 1841 1840 1 1841 1842 1 1842 1840 1 1841 1843 1 1843 1842 1 1843 1844 1 1844 1842 1
		 1843 1845 1 1845 1844 1 1845 1846 1 1846 1844 1 1846 1839 1 1839 1844 1 1847 1839 1
		 1846 1847 1 1846 1848 1 1848 1847 1 1848 1849 1 1849 1847 1 1850 1847 1 1849 1850 1
		 1849 1851 1 1851 1850 1 1849 1852 1 1852 1851 1 1853 1851 1 1852 1853 1 1854 1853 1
		 1852 1854 1 1855 1854 1 1852 1855 1 1852 1856 1 1856 1855 1 1856 1857 1 1857 1855 1
		 1857 1858 1 1858 1855 1 1859 1855 1 1858 1859 1 1858 1860 1 1860 1859 1 1860 1861 1
		 1861 1859 1 1860 1862 1 1862 1861 1 1862 1863 1 1863 1861 1 1864 1861 1 1863 1864 1
		 1865 1864 1 1863 1865 1 1866 1865 1 1863 1866 1 1863 1867 1 1867 1866 1 1867 1868 1
		 1868 1866 1 1868 1869 1 1869 1866 1 1870 1866 1 1869 1870 1 1871 1870 1 1869 1871 1
		 1872 1871 1 1869 1872 1 1869 1873 1 1873 1872 1 1874 1872 1 1873 1874 1 1873 1875 1
		 1875 1874 1 742 1874 1 1875 742 1 1873 1876 1 1876 1875 1 1877 1875 1 1876 1877 1
		 1876 1878 1 1878 1877 1 1878 1879 1 1879 1877 1 1879 1880 1 1880 1877 1 1879 1881 1
		 1881 1880 1 1881 1882 1 1882 1880 1 1883 1882 1 1881 1883 1 1883 1884 1 1884 1882 1
		 1877 1882 1 1884 1877 1 739 1877 1 1884 739 1 1885 739 1 1884 1885 1 1886 739 1 1885 1886 0
		 1883 1885 1 1883 1887 1 1887 1885 0 1883 1888 1 1888 1887 0 1883 1879 1 1879 1888 1
		 1879 1889 1 1889 1888 1 1879 1890 1 1890 1889 1 1890 1891 1 1891 1889 1 1890 1892 1
		 1892 1891 0 1890 1893 1 1893 1892 1 1894 1892 0 1893 1894 1 1893 1895 1 1895 1894 1
		 1896 1894 0 1895 1896 1 1895 1897 1 1897 1896 1 1897 1898 1 1898 1896 0 1899 1898 0
		 1897 1899 1 1900 1899 1 1897 1900 1 1901 1900 1 1897 1901 1 1902 1900 1 1901 1902 1
		 1903 1902 1 1901 1903 1 1901 1895 1 1895 1903 1 1895 1904 1 1904 1903 1 1904 1905 1
		 1905 1903 1 1905 1906 1 1906 1903 1 1907 1906 1 1905 1907 1 1908 1907 1 1905 1908 1
		 1905 1909 1 1909 1908 1 1909 1910 1 1910 1908 1 1910 1911 1 1911 1908 1 1912 1911 1
		 1910 1912 1 1910 1913 1 1913 1912 1 1914 1912 1 1913 1914 1 1913 1915 1;
	setAttr ".ed[5146:5311]" 1915 1914 1 1916 1914 1 1915 1916 1 1915 1917 1 1917 1916 1
		 1918 1916 1 1917 1918 1 1919 1918 1 1917 1919 1 1920 1919 1 1917 1920 1 1917 1921 1
		 1921 1920 1 1917 1890 1 1890 1921 1 1917 1909 1 1909 1890 1 1909 1922 1 1922 1890 1
		 1909 1893 1 1893 1922 1 1909 1904 1 1904 1893 1 1921 1876 1 1876 1920 1 1868 1919 1
		 1920 1868 1 1920 1873 1 1873 1868 1 1868 1918 1 1863 1916 1 1918 1863 1 1915 1909 1
		 1916 1923 1 1923 1914 1 1916 1924 1 1924 1923 1 1924 1925 1 1925 1923 1 1924 1926 1
		 1926 1925 1 1926 1927 1 1927 1925 1 1927 1928 1 1928 1925 1 1927 1929 1 1929 1928 1
		 1929 1930 0 1930 1928 1 1930 1931 1 1931 1928 1 1911 1928 1 1931 1911 1 1931 1932 1
		 1932 1911 1 1932 1907 1 1907 1911 1 1931 1933 1 1933 1932 1 1933 1934 1 1934 1932 1
		 1934 1902 1 1902 1932 1 1906 1932 1 1902 1906 1 1935 1934 1 1933 1935 1 1936 1935 1
		 1933 1936 1 1933 1937 1 1937 1936 1 1938 1936 1 1937 1938 1 1939 1938 1 1937 1939 0
		 1939 1940 0 1940 1938 1 1940 1941 1 1941 1938 1 1941 1942 1 1942 1938 1 1941 1943 1
		 1943 1942 1 1943 1944 1 1944 1942 1 1944 1935 1 1935 1942 1 1944 1945 1 1945 1935 1
		 1944 1946 1 1946 1945 1 1946 1947 1 1947 1945 1 1900 1945 1 1947 1900 1 1934 1945 1
		 1900 1934 1 1946 1899 0 1899 1947 1 1944 1948 1 1948 1946 0 1943 1948 0 1949 1943 1
		 1941 1949 1 1941 1950 1 1950 1949 1 1951 1949 1 1950 1951 0 1952 1949 1 1951 1952 0
		 1952 1953 1 1953 1949 1 1954 1953 1 1952 1954 0 1954 1955 1 1955 1953 0 1956 1955 0
		 1954 1956 0 1953 1943 0 1940 1950 0 1942 1936 1 1933 1957 1 1957 1937 0 1958 1957 0
		 1933 1958 1 1931 1958 1 1930 1958 0 1927 1959 1 1959 1929 0 1960 1959 1 1927 1960 1
		 1961 1960 1 1927 1961 1 1961 1962 1 1962 1960 1 1962 1963 1 1963 1960 1 1962 1964 1
		 1964 1963 0 1962 1965 1 1965 1964 0 1962 143 1 143 1965 1 1966 143 1 1962 1966 1
		 1967 1966 1 1962 1967 1 1968 1967 1 1962 1968 1 1969 1968 1 1962 1969 1 1962 1970 1
		 1970 1969 1 1970 1971 1 1971 1969 1 1970 1972 1 1972 1971 1 1972 1973 1 1973 1971 1
		 1974 1971 1 1973 1974 1 1973 1975 1 1975 1974 1 1816 1974 1 1975 1816 1 1816 1976 1;
	setAttr ".ed[5312:5477]" 1976 1974 1 1976 1977 1 1977 1974 1 1976 1968 1 1968 1977 1
		 1968 1971 1 1971 1977 1 1978 1968 1 1976 1978 1 1976 1814 1 1814 1978 1 1814 1979 1
		 1979 1978 1 1979 1980 1 1980 1978 1 1979 1981 1 1981 1980 1 1981 1966 1 1966 1980 1
		 1982 1966 1 1981 1982 1 1982 1983 1 1983 1966 1 145 1966 1 1983 145 1 1982 146 1
		 146 1983 1 1979 1982 1 1809 1982 1 1979 1809 1 1984 1982 1 1809 1984 1 1809 1985 1
		 1985 1984 1 151 1984 1 1985 151 1 1986 151 1 1985 1986 1 1805 1986 1 1985 1805 1
		 1805 1987 1 1987 1986 1 156 1986 1 1987 156 1 1987 1988 1 1988 156 1 1987 1989 1
		 1989 1988 1 1989 164 1 164 1988 1 158 1988 1 164 158 1 1989 1990 1 1990 164 1 1989 1991 1
		 1991 1990 1 1991 1799 1 1799 1990 1 1799 1992 1 1992 1990 1 1992 1993 1 1993 1990 1
		 165 1990 1 1993 165 1 1992 1798 1 1798 1993 1 1798 1775 1 1775 1993 1 1775 167 1
		 167 1993 1 1987 1991 1 1987 1803 1 1803 1991 1 1984 150 1 150 1982 1 1814 1809 1
		 1980 1968 1 1973 1994 1 1994 1975 1 1994 1819 1 1819 1975 1 1994 1995 1 1995 1819 1
		 1973 1995 1 1972 1995 1 1972 1996 1 1996 1995 1 1996 1820 1 1820 1995 1 1996 1970 1
		 1970 1820 1 1970 1852 1 1852 1820 1 1997 1820 1 1852 1997 1 1962 1998 1 1998 1970 1
		 1998 1857 1 1857 1970 1 1998 1999 1 1999 1857 1 1999 2000 1 2000 1857 1 1962 2000 1
		 1999 1962 1 2001 1857 1 2000 2001 1 2000 2002 1 2002 2001 1 2002 2003 1 2003 2001 1
		 2003 2004 1 2004 2001 1 2003 2005 1 2005 2004 1 2003 1926 1 1926 2005 1 1926 1862 1
		 1862 2005 1 1862 2006 1 2006 2005 1 2007 1926 1 2003 2007 1 1961 1926 1 2007 1961 1
		 2002 1961 1 2007 2002 1 2006 2004 1 1858 2004 1 2006 1858 1 1858 2001 1 2000 1961 1
		 1980 1967 1 1963 1959 0 1924 1862 1 1928 1923 1 1928 1912 1 1912 1923 1 1916 1862 1
		 1910 1915 1 1879 1921 1 1891 1888 0 1878 1921 1 740 1875 1 1877 740 1 742 1872 1
		 742 765 1 765 1872 1 765 2008 1 2008 1872 1 2008 1871 1 2008 2009 1 2009 1871 1 2008 1850 1
		 1850 2009 1 1850 1853 1 1853 2009 1 1870 2009 1 1853 1870 1 2008 2010 1 2010 1850 1
		 2010 1838 1 1838 1850 1 2010 2011 1 2011 1838 1 2011 793 1;
	setAttr ".ed[5478:5643]" 793 1838 1 2012 1838 1 793 2012 1 793 2013 1 2013 2012 1
		 2013 1793 1 1793 2012 1 2013 2014 1 2014 1793 1 2015 2014 1 2013 2015 1 794 2015 1
		 2013 794 1 2016 2015 1 794 2016 1 2017 2015 1 2016 2017 1 2016 2018 1 2018 2017 1
		 2018 2019 1 2019 2017 1 2019 2020 1 2020 2017 1 2020 2021 1 2021 2017 1 2020 2014 1
		 2014 2021 1 2019 2014 1 1792 2014 1 2019 1792 1 2018 2022 1 2022 2019 1 1788 2019 1
		 2022 1788 1 2018 2023 1 2023 2022 1 2018 2024 1 2024 2023 1 2024 2025 1 2025 2023 1
		 2025 2026 1 2026 2023 1 2027 2023 1 2026 2027 1 2026 2028 1 2028 2027 1 2028 2029 1
		 2029 2027 1 2022 2027 1 2029 2022 1 2029 1786 1 1786 2022 1 2028 845 1 845 2029 1
		 1785 2029 1 845 1785 1 845 2030 1 2030 1785 1 2026 2031 1 2031 2028 1 2031 843 1
		 843 2028 1 2026 2032 1 2032 2031 1 839 2031 1 2032 839 1 2033 2032 1 2026 2033 1
		 2034 2032 1 2033 2034 1 2033 797 1 797 2034 1 797 801 1 801 2034 1 801 835 1 835 2034 1
		 2033 2035 1 2035 797 1 2033 2025 1 2025 2035 1 2034 837 1 837 2032 1 2024 2035 1
		 796 2035 1 2024 796 1 2024 2036 1 2036 796 1 2036 2016 1 2016 796 1 2018 2036 1 2021 2015 1
		 1793 1837 1 1837 2012 1 2011 771 1 771 793 1 2010 768 1 768 2011 1 2008 768 1 1853 1866 1
		 1867 1918 1 1853 1865 1 1865 1854 1 1854 1864 1 1854 1859 1 1859 1864 1 1860 2006 1
		 1856 1970 1 1849 1997 1 2037 1997 1 1849 2037 1 2037 1821 1 1821 1997 1 1838 1847 1
		 1848 2037 1 1848 1826 1 1826 2037 1 1845 1848 1 1845 2038 1 2038 1848 1 1845 1830 1
		 1830 2038 1 2038 1829 1 1829 1848 1 1843 1830 1 1841 1830 1 1844 1840 1 1837 2039 1
		 2039 1835 1 2039 1808 1 1808 1835 1 2040 1808 1 2039 2040 1 2039 2041 1 2041 2040 1
		 2041 2042 1 2042 2040 1 2042 1801 1 1801 2040 1 2043 2040 1 1801 2043 1 2043 1807 1
		 1807 2040 1 1802 1807 1 2043 1802 1 1796 1801 1 2042 1796 1 2041 1795 1 1795 2042 1
		 1837 2041 1 1837 1794 1 1794 2041 1 1811 1827 1 1811 1825 1 1823 2037 1 1824 1818 1
		 1813 1818 1 1824 1813 1 1817 1975 1 1806 1985 1 1800 1991 1 2019 1790 1 2030 1783 1
		 2030 848 1 848 1783 1 1782 1787 1 1783 850 1;
	setAttr ".ed[5644:5809]" 850 1770 1 1779 1789 1 1773 167 1 171 167 1 1767 176 1
		 2030 846 1 844 856 1 2031 841 1 830 824 1 822 2044 1 2044 825 1 714 825 1 2044 714 1
		 715 2044 1 833 807 1 808 715 1 835 803 1 789 798 1 771 791 1 777 781 1 781 786 1
		 787 817 1 769 772 1 764 776 1 762 744 1 744 760 1 760 747 1 747 754 1 756 783 1 753 783 1
		 760 745 1 1886 738 1 1886 2045 1 2045 738 1 1886 2046 0 2046 2045 1 734 2045 1 2046 734 0
		 2045 735 1 717 808 1 716 2047 0 2047 713 1 2047 2048 0 2048 713 1 712 825 1 2048 711 0
		 692 872 1 710 608 1 693 685 1 693 632 1 693 612 1 612 632 1 612 620 1 620 632 1 682 1750 1
		 681 1750 1 679 1752 1 633 674 1 660 674 1 633 660 1 652 1108 1 2049 653 1 640 2049 1
		 647 653 1 2049 647 1 647 651 1 2049 645 1 2049 641 1 657 636 1 635 1735 1 629 1735 1
		 635 629 1 632 2050 1 2050 630 1 632 2051 1 2051 2050 1 628 2050 1 2051 628 1 622 628 1
		 2051 622 1 632 621 1 621 2051 1 628 624 1 623 1153 1 619 1153 1 617 1153 1 597 591 1
		 591 595 1 588 1169 1 604 585 1 605 582 0 577 1725 1 2052 1725 1 577 2052 1 572 1725 1
		 2052 572 1 572 567 1 567 1725 1 574 2052 1 576 548 1 548 575 1 552 575 1 548 552 1
		 573 2052 1 554 570 1 570 555 1 555 569 1 555 2053 1 2053 569 1 561 569 1 2053 561 1
		 559 2053 1 555 559 1 532 1218 1 550 558 1 536 558 1 550 536 1 550 542 1 542 536 1
		 576 547 0 545 540 1 2054 540 1 545 2054 0 2054 539 1 2055 539 1 2054 2055 1 2054 2056 1
		 2056 2055 1 2056 534 1 534 2055 1 538 2055 1 534 538 1 2056 2057 1 2057 534 1 2057 527 1
		 527 534 1 2058 527 1 2057 2058 1 2056 2058 1 2059 2058 1 2056 2059 1 2060 2059 1
		 2056 2060 1 2061 2060 0 2056 2061 1 2062 2059 1 2060 2062 0 2062 2063 0 2063 2059 1
		 2063 2058 1 526 2058 1 2063 526 1 2063 2064 0 2064 526 1 2064 2065 0 2065 526 1 2066 526 1
		 2065 2066 1 2065 521 1 521 2066 1 2065 513 0 513 521 1 2054 2061 0 533 558 1 2066 522 1
		 523 1239 1;
	setAttr ".ed[5810:5975]" 520 1239 1 516 1721 1 446 1721 1 510 2067 1 2067 509 1
		 510 2068 0 2068 2067 1 2068 504 0 504 2067 1 505 509 1 2067 505 1 475 447 0 436 1719 1
		 435 1719 1 438 430 1 439 427 0 427 2069 0 2069 426 1 2069 424 1 419 424 1 2069 419 0
		 418 413 1 389 410 1 394 406 1 409 394 1 401 1326 1 402 396 1 397 2070 1 2070 398 1
		 397 386 1 386 2070 1 384 398 1 2070 384 1 409 393 1 410 391 1 410 390 1 415 387 0
		 2071 382 0 385 2071 1 385 2072 0 2072 2071 0 376 1708 1 377 372 0 372 369 0 2073 361 1
		 362 2073 0 2073 360 0 360 2074 0 2074 352 1 2074 351 0 347 1028 1 349 2075 1 2075 348 1
		 2076 2075 1 349 2076 0 2077 2075 1 2076 2077 0 2077 2078 1 2078 2075 1 2079 2078 1
		 2077 2079 0 2079 2080 1 2080 2078 1 2079 2081 1 2081 2080 1 2079 2082 0 2082 2081 1
		 2082 2083 0 2083 2081 1 2084 2081 1 2083 2084 1 2083 2085 1 2085 2084 1 2085 2086 1
		 2086 2084 1 2087 2086 1 2085 2087 1 2085 2088 1 2088 2087 1 2089 2087 1 2088 2089 1
		 2088 2090 1 2090 2089 1 2090 2091 1 2091 2089 1 2090 2092 0 2092 2091 1 2092 2093 0
		 2093 2091 1 2093 2094 1 2094 2091 1 2095 2094 1 2093 2095 0 2096 2094 1 2095 2096 1
		 2097 2096 1 2095 2097 0 2098 2096 1 2097 2098 1 2099 2098 1 2097 2099 0 2099 2100 1
		 2100 2098 1 2101 2098 1 2100 2101 1 2100 2102 1 2102 2101 1 2102 2103 1 2103 2101 1
		 2103 2104 1 2104 2101 1 2105 2101 1 2104 2105 1 2106 2105 1 2104 2106 1 2107 2106 1
		 2104 2107 1 2107 2108 1 2108 2106 1 2108 2109 1 2109 2106 1 2109 2110 1 2110 2106 1
		 2109 2111 1 2111 2110 1 2112 2111 1 2109 2112 1 2113 2111 1 2112 2113 0 2114 2111 1
		 2113 2114 1 2113 2115 1 2115 2114 1 2116 2115 1 2113 2116 1 2113 2117 1 2117 2116 1
		 2117 2118 1 2118 2116 1 2117 2119 1 2119 2118 1 2119 2120 1 2120 2118 1 2121 2118 1
		 2120 2121 1 2122 2121 1 2120 2122 1 2123 2122 1 2120 2123 1 2124 2123 1 2120 2124 1
		 2125 2124 1 2120 2125 1 2126 2125 1 2120 2126 1 2127 2126 1 2120 2127 1 2127 2128 1
		 2128 2126 1 2128 2129 1 2129 2126 1 2130 2129 1 2128 2130 1 2128 345 1 345 2130 1
		 2131 345 1;
	setAttr ".ed[5976:6141]" 2128 2131 1 2132 345 1 2131 2132 1 2131 2133 1 2133 2132 1
		 2131 2134 1 2134 2133 1 2134 2135 1 2135 2133 1 2134 2136 1 2136 2135 1 2136 2137 1
		 2137 2135 1 2138 2137 1 2136 2138 1 2138 2139 1 2139 2137 1 2139 336 1 336 2137 1
		 2138 2140 1 2140 2139 1 335 2139 1 2140 335 1 2140 2141 1 2141 335 1 2141 2142 1
		 2142 335 1 2141 2143 1 2143 2142 1 2141 2144 1 2144 2143 1 2145 2143 0 2144 2145 1
		 2144 2146 1 2146 2145 0 2117 2146 1 2144 2117 1 2141 2119 1 2119 2144 1 2141 2147 1
		 2147 2119 1 2148 2119 1 2147 2148 1 2147 2138 1 2138 2148 1 2134 2148 1 2138 2134 1
		 2134 2119 1 2134 2127 1 2127 2119 1 2143 2149 0 2149 2142 1 2149 332 1 332 2142 1
		 2149 2150 0 2150 332 1 2151 332 1 2150 2151 0 2140 2147 1 2137 343 1 343 2135 1 2137 338 1
		 338 343 1 2131 2127 1 2135 2132 1 2135 345 1 2130 346 1 346 2129 1 346 2075 1 2075 2129 1
		 2129 2078 1 2078 2126 1 2126 2084 1 2084 2125 1 2126 2080 1 2080 2084 1 2125 2089 1
		 2089 2124 1 2124 2091 1 2091 2123 1 2091 2122 1 2122 2094 1 2094 2121 1 2152 2121 1
		 2094 2152 1 2094 2153 1 2153 2152 1 2094 2098 1 2098 2153 1 2153 2114 1 2114 2152 1
		 2153 2110 1 2110 2114 1 2105 2110 1 2153 2105 1 2114 2121 1 2114 2154 1 2154 2121 1
		 2154 2118 1 2154 2115 1 2115 2118 1 2113 2146 0 2108 2112 1 2108 2155 1 2155 2112 0
		 2107 2155 1 2107 2156 1 2156 2155 0 2103 2156 0 2107 2103 1 2153 2101 1 2157 2103 0
		 2102 2157 1 2102 2158 1 2158 2157 0 2100 2158 1 2099 2158 0 2159 2090 0 2088 2159 1
		 2125 2087 1 2085 2159 1 2085 2160 1 2160 2159 1 2160 2161 0 2161 2159 0 2125 2086 1
		 2083 2160 0 342 1028 1 2135 344 1 328 1017 1 2151 331 1 2162 331 1 2151 2162 0 2162 330 1
		 2163 330 1 2162 2163 0 318 330 1 2163 318 1 2163 2164 0 2164 318 1 320 324 1 324 329 1
		 325 1015 1 319 1042 1 316 1042 1 2164 317 1 2164 2165 0 2165 317 1 2165 309 1 309 317 1
		 2165 2166 0 2166 309 1 2166 2167 0 2167 309 1 2168 309 1 2167 2168 1 2167 2169 0
		 2169 2168 1 2169 2170 1 2170 2168 1 2170 2171 1 2171 2168 1 2171 2172 1 2172 2168 1
		 2171 2173 1 2173 2172 1;
	setAttr ".ed[6142:6307]" 2173 2174 1 2174 2172 1 307 2172 1 2174 307 1 2174 2175 1
		 2175 307 1 2176 2175 1 2174 2176 1 2176 2177 1 2177 2175 1 2176 2178 1 2178 2177 1
		 2178 2179 1 2179 2177 1 2179 2180 1 2180 2177 1 2179 2181 1 2181 2180 1 2181 2182 1
		 2182 2180 1 2181 2183 1 2183 2182 1 2183 2184 1 2184 2182 1 2184 2185 1 2185 2182 1
		 2184 2186 1 2186 2185 1 2187 2185 1 2186 2187 1 2186 2188 1 2188 2187 1 2188 2189 1
		 2189 2187 1 2189 2190 1 2190 2187 1 2190 2191 1 2191 2187 1 2191 2192 1 2192 2187 1
		 2191 262 1 262 2192 1 2191 252 1 252 262 1 2190 252 1 2190 2193 1 2193 252 1 2194 2193 1
		 2190 2194 1 2194 243 1 243 2193 1 250 2193 1 243 250 1 2195 243 1 2194 2195 1 2194 2189 1
		 2189 2195 1 225 243 1 2195 225 1 2196 225 1 2195 2196 1 2188 2196 1 2195 2188 1 2188 2197 1
		 2197 2196 1 2197 2198 1 2198 2196 1 2198 2199 1 2199 2196 1 2200 2199 1 2198 2200 1
		 2201 2200 1 2198 2201 1 2198 2202 1 2202 2201 1 2202 2203 1 2203 2201 1 2203 2204 1
		 2204 2201 1 2204 2205 1 2205 2201 1 2205 2206 1 2206 2201 1 2205 219 1 219 2206 1
		 223 2206 1 219 223 1 2199 2206 1 223 2199 1 2205 215 1 215 219 1 2204 214 1 214 2205 1
		 2203 2207 1 2207 2204 1 2207 2208 1 2208 2204 1 2208 213 1 213 2204 1 2208 2209 1
		 2209 213 1 2208 2210 1 2210 2209 1 2211 2210 1 2208 2211 1 2212 2210 1 2211 2212 1
		 2211 2213 1 2213 2212 1 2211 2214 1 2214 2213 1 2211 2207 1 2207 2214 1 2214 2181 1
		 2181 2213 1 2215 2212 1 2213 2215 1 2213 2216 1 2216 2215 1 2216 2217 1 2217 2215 1
		 2218 2215 1 2217 2218 1 2219 2218 1 2217 2219 1 2220 2218 1 2219 2220 1 2219 2221 1
		 2221 2220 1 2219 2222 1 2222 2221 1 2222 2173 1 2173 2221 1 2222 2176 1 2176 2173 1
		 2222 2223 1 2223 2176 1 2219 2223 1 2219 2216 1 2216 2223 1 2216 2178 1 2178 2223 1
		 2224 2220 1 2221 2224 1 2221 2225 1 2225 2224 1 2226 2224 1 2225 2226 1 2227 2226 1
		 2225 2227 1 2225 2228 1 2228 2227 1 2228 2229 1 2229 2227 1 2228 2230 1 2230 2229 1
		 2230 2231 1 2231 2229 1 2232 2229 1 2231 2232 1 2231 2233 1 2233 2232 1 2231 2234 1
		 2234 2233 1 2234 2235 1 2235 2233 1;
	setAttr ".ed[6308:6473]" 2235 2236 1 2236 2233 1 2236 2237 1 2237 2233 1 2236 2238 1
		 2238 2237 1 2238 2239 1 2239 2237 1 2239 2232 1 2232 2237 1 2239 2240 1 2240 2232 1
		 2239 2241 1 2241 2240 1 2241 2242 1 2242 2240 1 2242 2226 1 2226 2240 1 2243 2226 1
		 2242 2243 1 2244 2243 1 2242 2244 1 2245 2243 1 2244 2245 1 2246 2245 1 2244 2246 1
		 2244 2241 1 2241 2246 1 2238 2246 1 2241 2238 1 2238 2247 1 2247 2246 1 2248 2247 1
		 2238 2248 1 2238 2249 1 2249 2248 1 2249 2250 1 2250 2248 1 2251 2248 1 2250 2251 1
		 2252 2251 1 2250 2252 1 2250 2253 1 2253 2252 1 2253 2254 1 2254 2252 1 2254 2255 1
		 2255 2252 1 2254 2256 1 2256 2255 1 2257 2255 1 2256 2257 1 2256 2258 1 2258 2257 1
		 2258 2259 1 2259 2257 1 2259 2260 1 2260 2257 1 2260 2261 1 2261 2257 1 2262 2261 1
		 2260 2262 1 2263 2262 1 2260 2263 1 2264 2262 1 2263 2264 1 2265 2264 1 2263 2265 1
		 2263 138 1 138 2265 1 2263 2266 1 2266 138 1 2263 2259 1 2259 2266 1 2259 2267 1
		 2267 2266 1 2267 135 1 135 2266 1 2267 2268 1 2268 135 1 2267 2269 1 2269 2268 1
		 2269 113 1 113 2268 1 2270 2269 1 2267 2270 1 2267 2258 1 2258 2270 1 2258 2271 1
		 2271 2270 1 2272 2270 1 2271 2272 1 2235 2272 1 2271 2235 1 2253 2235 1 2271 2253 1
		 2271 2256 1 2256 2253 1 2253 2249 1 2249 2235 1 2272 2273 1 2273 2270 1 2273 112 1
		 112 2270 1 2273 2274 1 2274 112 1 2274 2275 1 2275 112 1 2274 94 1 94 2275 1 94 100 1
		 100 2275 1 100 109 1 109 2275 1 2273 2276 1 2276 2274 1 2273 2277 1 2277 2276 1 2277 2278 1
		 2278 2276 1 2277 2279 1 2279 2278 1 2280 2278 1 2279 2280 1 2279 2281 1 2281 2280 1
		 2231 2281 1 2279 2231 1 2281 2282 1 2282 2280 1 2282 2283 0 2283 2280 1 2281 2230 1
		 2230 2282 1 2284 2282 0 2230 2284 1 2230 2285 1 2285 2284 0 2286 2285 1 2230 2286 1
		 2286 2287 1 2287 2285 0 2286 2288 1 2288 2287 0 2286 2170 1 2170 2288 1 2228 2170 1
		 2286 2228 1 2283 2278 1 2283 2289 0 2289 2278 1 2289 2290 1 2290 2278 1 2291 2290 1
		 2289 2291 0 2292 2290 1 2291 2292 1 2291 2293 1 2293 2292 1 2293 2294 1 2294 2292 1
		 2295 2292 1 2294 2295 1 2296 2295 1 2294 2296 1 2296 87 1;
	setAttr ".ed[6474:6639]" 87 2295 1 2297 2295 1 87 2297 1 2297 2290 1 2290 2295 1
		 2276 2290 1 2297 2276 1 2293 2296 1 2293 2298 1 2298 2296 1 2298 86 1 86 2296 1 2298 84 1
		 84 86 1 2298 2299 1 2299 84 1 2299 2300 0 2300 84 1 2293 2299 1 2291 2299 0 2277 2231 1
		 2297 2274 1 2297 91 1 91 2274 1 2272 2277 1 2272 2234 1 2234 2277 1 112 2269 1 2301 2264 1
		 2265 2301 1 2265 147 1 147 2301 1 2302 2301 1 147 2302 1 2302 2303 1 2303 2301 1
		 2302 2304 1 2304 2303 1 2304 2305 1 2305 2303 1 2304 2306 1 2306 2305 1 2304 2307 1
		 2307 2306 1 2308 2306 1 2307 2308 1 2307 2309 1 2309 2308 1 2310 2308 1 2309 2310 1
		 2309 2311 1 2311 2310 1 2311 2312 1 2312 2310 1 2312 2313 1 2313 2310 1 2312 2314 1
		 2314 2313 1 2314 2315 1 2315 2313 1 2316 2313 1 2315 2316 1 2315 2317 1 2317 2316 1
		 2317 2318 1 2318 2316 1 2318 2308 1 2308 2316 1 2319 2318 1 2317 2319 1 2320 2319 1
		 2317 2320 1 2317 2321 1 2321 2320 1 2261 2320 1 2321 2261 1 2321 2255 1 2255 2261 1
		 2321 2322 1 2322 2255 1 2317 2322 1 2320 2262 1 2262 2319 1 2305 2318 1 2319 2305 1
		 2315 2322 1 2315 2252 1 2252 2322 1 2315 2323 1 2323 2252 1 2308 2313 1 2314 2323 1
		 2314 2324 1 2324 2323 1 2324 2245 1 2245 2323 1 2245 2247 1 2247 2323 1 2325 2323 1
		 2247 2325 1 2325 2251 1 2251 2323 1 2314 2326 1 2326 2324 1 2326 2327 1 2327 2324 1
		 2327 2243 1 2243 2324 1 2327 2328 1 2328 2243 1 2328 2329 1 2329 2243 1 2330 2329 1
		 2328 2330 1 2330 2220 1 2220 2329 1 2331 2220 1 2330 2331 1 2330 2332 1 2332 2331 1
		 2332 2333 1 2333 2331 1 2333 2334 1 2334 2331 1 2334 2335 1 2335 2331 1 2334 2336 1
		 2336 2335 1 2334 2337 1 2337 2336 1 2209 2336 1 2337 2209 1 2337 2338 1 2338 2209 1
		 2337 2339 1 2339 2338 1 2339 2340 1 2340 2338 1 2340 2341 1 2341 2338 1 2340 2342 1
		 2342 2341 1 2342 2343 1 2343 2341 1 2343 2344 1 2344 2341 1 2345 2344 1 2343 2345 1
		 2346 2345 1 2343 2346 1 2347 2345 1 2346 2347 1 2346 2348 1 2348 2347 1 2348 2349 1
		 2349 2347 1 2348 2350 1 2350 2349 1 2350 212 1 212 2349 1 212 2351 1 2351 2349 1
		 212 2352 1 2352 2351 1 2353 2351 1 2352 2353 1;
	setAttr ".ed[6640:6805]" 2352 2345 1 2345 2353 1 2347 2351 1 2353 2347 1 212 2209 1
		 2209 2352 1 2209 2344 1 2344 2352 1 2348 2354 1 2354 2350 1 2354 2355 1 2355 2350 1
		 2355 2356 1 2356 2350 1 2356 211 1 211 2350 1 2355 2357 1 2357 2356 1 2355 2358 1
		 2358 2357 1 179 2357 1 2358 179 1 2359 179 1 2358 2359 1 2360 2359 1 2358 2360 1
		 2354 2360 1 2358 2354 1 2354 2361 1 2361 2360 1 2361 2362 1 2362 2360 1 2362 2363 1
		 2363 2360 1 2362 162 1 162 2363 1 162 2364 1 2364 2363 1 162 169 1 169 2364 1 169 174 1
		 174 2364 1 2364 2359 1 2359 2363 1 2365 2362 1 2361 2365 1 2365 2366 1 2366 2362 1
		 2367 2362 1 2366 2367 1 2368 2367 1 2366 2368 1 2369 2368 1 2366 2369 1 2369 2370 1
		 2370 2368 1 2370 2371 1 2371 2368 1 2372 2371 1 2370 2372 1 2370 2373 1 2373 2372 1
		 159 2372 1 2373 159 1 2373 2374 1 2374 159 1 2374 2375 1 2375 159 1 2376 159 1 2375 2376 1
		 2377 2376 1 2375 2377 1 2378 2376 1 2377 2378 1 2377 2379 1 2379 2378 1 2380 2378 1
		 2379 2380 1 2309 2380 1 2379 2309 1 2379 2381 1 2381 2309 1 2382 2309 1 2381 2382 1
		 2383 2382 1 2381 2383 1 2381 2384 1 2384 2383 1 2385 2383 1 2384 2385 1 2384 2386 1
		 2386 2385 1 2384 2373 1 2373 2386 1 2386 2369 1 2369 2385 1 2369 2365 1 2365 2385 1
		 2387 2385 1 2365 2387 1 2354 2387 1 2365 2354 1 2387 2383 1 2381 2374 1 2374 2384 1
		 2381 2377 1 2377 2374 1 2387 2382 1 2387 2311 1 2311 2382 1 2388 2311 1 2387 2388 1
		 2389 2388 1 2387 2389 1 2390 2389 1 2387 2390 1 2387 2342 1 2342 2390 1 2348 2342 1
		 2387 2348 1 2390 2333 1 2333 2389 1 2333 2391 1 2391 2389 1 2312 2389 1 2391 2312 1
		 2391 2326 1 2326 2312 1 2391 2332 1 2332 2326 1 2332 2392 1 2392 2326 1 2390 2337 1
		 2337 2333 1 2312 2388 1 2393 2378 1 2380 2393 1 2380 2307 1 2307 2393 1 2394 2378 1
		 2393 2394 1 2302 2394 1 2393 2302 1 154 2394 1 2302 154 1 2302 149 1 149 154 1 2394 157 1
		 157 2378 1 157 2376 1 159 2395 1 2395 2372 1 2370 2386 1 2395 2371 1 2395 2367 1
		 2367 2371 1 161 2367 1 2395 161 1 161 2362 1 2364 179 1 2357 208 1 208 2356 1 2346 2342 1
		 2340 2390 1 2344 2338 1 2339 2390 1;
	setAttr ".ed[6806:6971]" 2210 2335 1 2336 2210 1 2210 2396 1 2396 2335 1 2396 2331 1
		 2330 2392 1 2330 2327 1 2327 2392 1 2396 2220 1 2318 2306 1 2304 2393 1 2319 2303 1
		 2319 2264 1 2264 2303 1 2325 2248 1 2329 2226 1 2227 2232 1 2240 2227 1 2236 2249 1
		 2225 2170 1 2329 2224 1 2221 2171 1 2171 2225 1 2396 2218 1 2396 2212 1 2212 2218 1
		 2213 2179 1 2179 2216 1 2203 2214 1 2202 2214 1 2202 2183 1 2183 2214 1 2202 2197 1
		 2197 2183 1 2206 2200 1 2188 2184 1 2184 2197 1 2199 225 1 2192 2185 1 2180 2185 1
		 2192 2180 1 2192 2177 1 2192 294 1 294 2177 1 2192 263 1 263 294 1 2177 304 1 304 2175 1
		 2177 295 1 295 304 1 307 2168 1 2169 2288 0 317 311 1 310 285 1 285 312 1 310 2397 1
		 2397 285 1 2397 299 1 299 285 1 308 2397 1 306 2397 1 306 302 1 302 2397 1 2175 305 1
		 300 2397 1 304 297 1 296 289 1 263 293 1 263 269 1 269 293 1 272 291 1 293 272 1
		 290 296 1 287 299 1 288 275 1 275 284 1 286 299 1 277 1079 1 277 2398 1 2398 1079 1
		 2399 1079 1 2398 2399 1 2398 257 1 257 2399 1 2398 2400 1 2400 257 1 2398 268 1 268 2400 1
		 2398 273 1 273 268 1 2400 267 1 267 257 1 2399 255 1 255 1079 1 293 270 1 263 266 1
		 260 265 1 251 1078 1 250 244 1 233 194 1 239 228 1 218 230 1 204 230 1 218 204 1
		 209 216 1 206 216 1 2357 207 1 2357 180 1 180 207 1 207 183 1 183 203 1 183 200 1
		 199 186 1 186 197 1 197 188 1 188 195 1 182 187 1 2364 175 1 162 166 1 2394 155 1
		 153 1986 1 148 1982 1 2265 144 1 2265 141 1 142 1965 1 142 2401 1 2401 1965 0 140 2401 0
		 134 137 0 2268 115 1 132 2402 1 2402 133 1 132 2403 1 2403 2402 1 2404 2402 1 2403 2404 0
		 2404 2405 1 2405 2402 1 2406 2405 0 2404 2406 1 2407 2406 0 2404 2407 0 132 2408 1
		 2408 2403 1 2408 2409 1 2409 2403 0 130 2409 1 2408 130 1 2405 133 0 115 118 1 128 2409 1
		 127 2409 1 126 2409 0 129 122 1 123 2410 1 2410 124 0 2411 2410 0 123 2411 1 123 2412 1
		 2412 2411 0 123 2413 1 2413 2412 0 123 2414 1 2414 2413 0 121 2414 1 121 2415 1;
	setAttr ".ed[6972:7137]" 2415 2414 0 129 119 1 120 2415 1 120 2416 1 2416 2415 0
		 120 2417 1 2417 2416 1 2417 2418 1 2418 2416 0 2417 2419 1 2419 2418 1 2419 2420 1
		 2420 2418 0 2419 2421 1 2421 2420 0 2419 2422 1 2422 2421 0 19 2422 1 2419 19 1 2423 19 1
		 2419 2423 1 2424 2422 0 19 2424 1 19 2425 1 2425 2424 1 2425 2426 1 2426 2424 0 2425 2427 1
		 2427 2426 1 2428 2426 0 2427 2428 1 2429 2428 1 2427 2429 1 2427 2430 1 2430 2429 1
		 2431 2429 1 2430 2431 1 2430 16 1 16 2431 0 2430 2432 1 2432 16 1 2431 2433 0 2433 2429 1
		 2427 2432 1 2433 2428 0 2425 2432 1 17 2432 1 2425 17 1 2417 2423 1 2417 2434 1 2434 2423 1
		 2434 2435 1 2435 2423 1 2435 20 1 20 2423 1 2434 107 1 107 2435 1 107 102 1 102 2435 1
		 102 26 1 26 2435 1 2434 2436 1 2436 107 1 2417 2436 1 120 2436 1 117 2436 1 117 108 1
		 108 2436 1 2268 114 1 2275 111 1 100 106 1 98 104 1 98 43 1 43 104 1 2437 104 1 43 2437 1
		 2437 32 1 32 104 1 2437 42 1 42 32 1 98 47 1 47 43 1 95 98 1 95 89 1 89 98 1 2274 93 1
		 2274 92 1 2297 88 1 2300 83 1 2300 2438 1 2438 83 1 2300 2439 0 2439 2438 1 2440 2438 1
		 2439 2440 1 2439 2441 0 2441 2440 1 2441 78 1 78 2440 1 2441 2442 0 2442 78 1 2443 78 1
		 2442 2443 0 2443 2444 0 2444 78 1 2444 74 1 74 78 1 2445 74 1 2444 2445 0 79 2438 1
		 2440 79 1 2438 80 1 2445 72 1 2445 2446 1 2446 72 1 2445 2447 0 2447 2446 1 2447 2448 1
		 2448 2446 1 2448 2449 1 2449 2446 1 2450 2449 1 2448 2450 1 2448 2451 1 2451 2450 1
		 2451 2452 0 2452 2450 1 2452 2453 0 2453 2450 1 2453 2449 1 2453 70 0 70 2449 1 71 2446 1
		 2449 71 1 2447 2451 1 2447 2454 0 2454 2451 1 2455 2451 0 2454 2455 0 65 76 1 66 57 0
		 57 64 1 57 62 1 61 77 1 57 60 1 57 2456 1 2456 56 1 57 2457 0 2457 2456 1 2458 2456 1
		 2457 2458 0 2458 37 1 37 2456 1 2458 2459 1 2459 37 1 2459 2460 1 2460 37 1 2460 33 1
		 33 37 1 2460 2461 1 2461 33 1 4 33 1 2461 4 0 2462 2461 0 2460 2462 1 2459 2462 1;
	setAttr ".ed[7138:7182]" 2459 2463 1 2463 2462 1 2464 2462 0 2463 2464 1 2458 2464 0
		 2463 2458 1 52 2456 1 37 52 1 53 82 1 38 49 1 40 45 1 4 31 1 30 104 1 2465 28 1 29 2465 1
		 29 1 1 1 2465 1 2465 21 1 21 28 1 24 28 1 21 24 1 0 21 1 2465 0 1 0 15 1 15 21 1
		 23 2435 1 2466 16 0 14 2466 1 13 2466 1 13 2467 1 2467 2466 0 12 2467 1 12 2468 1
		 2468 2467 1 12 7 1 7 2468 1 2469 2468 1 7 2469 1 2470 2468 1 2469 2470 0 2470 2467 1
		 2471 2467 0 2470 2471 0 6 2469 1 4 2469 0;
	setAttr -s 2472 ".n";
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
	setAttr ".n[1162:1327]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1328:1493]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1494:1659]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1660:1825]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1826:1991]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[1992:2157]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[2158:2323]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
	setAttr ".n[2324:2471]" -type "float3"  1e+20 1e+20 1e+20 1e+20 1e+20 1e+20 1e+20
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
		 1e+20 1e+20 1e+20;
	setAttr -s 4712 -ch 14136 ".fc";
	setAttr ".fc[0:499]" -type "polyFaces" 
		f 3 0 1 2
		mu 0 3 0 1 2
		f 3 -2 3 4
		mu 0 3 2 1 3
		f 3 -5 5 6
		mu 0 3 2 3 4
		f 3 -7 7 8
		mu 0 3 2 4 5
		f 3 9 10 -8
		mu 0 3 4 6 5
		f 3 11 12 -11
		mu 0 3 6 7 5
		f 3 13 14 -13
		mu 0 3 7 8 5
		f 3 15 16 -15
		mu 0 3 8 9 5
		f 3 17 -17 18
		mu 0 3 0 5 9
		f 3 -19 19 20
		mu 0 3 0 9 10
		f 3 -21 21 22
		mu 0 3 0 10 11
		f 3 23 -22 24
		mu 0 3 12 11 10
		f 3 25 -25 26
		mu 0 3 8 12 10
		f 3 27 28 -24
		mu 0 3 12 13 11
		f 3 29 30 -29
		mu 0 3 13 14 11
		f 3 31 32 -31
		mu 0 3 14 15 11
		f 3 33 34 -32
		mu 0 3 14 16 15
		f 3 -35 35 36
		mu 0 3 15 16 17
		f 3 37 -37 38
		mu 0 3 18 15 17
		f 3 -39 39 40
		mu 0 3 18 17 19
		f 3 41 42 -41
		mu 0 3 19 20 18
		f 3 43 44 -43
		mu 0 3 20 21 18
		f 3 -44 45 46
		mu 0 3 21 20 22
		f 3 47 48 -46
		mu 0 3 20 23 22
		f 3 49 50 -49
		mu 0 3 23 24 22
		f 3 51 -50 52
		mu 0 3 25 24 23
		f 3 53 54 -53
		mu 0 3 23 26 25
		f 3 55 56 -55
		mu 0 3 26 27 25
		f 3 57 -57 58
		mu 0 3 28 25 27
		f 3 59 -59 60
		mu 0 3 29 28 27
		f 3 61 62 -61
		mu 0 3 27 30 29
		f 3 63 64 -63
		mu 0 3 30 31 29
		f 3 65 -65 66
		mu 0 3 3 29 31
		f 3 67 68 -64
		mu 0 3 30 32 31
		f 3 -69 69 70
		mu 0 3 31 32 33
		f 3 -70 71 72
		mu 0 3 33 32 34
		f 3 73 74 -72
		mu 0 3 32 35 34
		f 3 75 76 -75
		mu 0 3 35 36 34
		f 3 77 -77 78
		mu 0 3 37 34 36
		f 3 -79 79 80
		mu 0 3 37 36 38
		f 3 81 -80 82
		mu 0 3 39 38 36
		f 3 83 -82 84
		mu 0 3 40 38 39
		f 3 85 -85 86
		mu 0 3 41 40 39
		f 3 -87 87 88
		mu 0 3 41 39 35
		f 3 89 -89 90
		mu 0 3 42 41 35
		f 3 91 92 -90
		mu 0 3 42 43 41
		f 3 93 94 -93
		mu 0 3 43 44 41
		f 3 95 96 -95
		mu 0 3 44 45 41
		f 3 -96 97 98
		mu 0 3 45 44 46
		f 3 99 100 -98
		mu 0 3 44 47 46
		f 3 101 102 -101
		mu 0 3 47 48 46
		f 3 103 104 -103
		mu 0 3 48 40 46
		f 3 105 106 -104
		mu 0 3 48 49 40
		f 3 107 -106 108
		mu 0 3 50 49 48
		f 3 109 -109 110
		mu 0 3 51 50 48
		f 3 -110 111 112
		mu 0 3 50 51 38
		f 3 113 114 -112
		mu 0 3 51 52 38
		f 3 115 116 -114
		mu 0 3 51 53 52
		f 3 117 118 -117
		mu 0 3 53 54 52
		f 3 119 120 -119
		mu 0 3 54 55 52
		f 3 121 -121 122
		mu 0 3 56 52 55
		f 3 123 -123 124
		mu 0 3 57 56 55
		f 3 125 -125 126
		mu 0 3 58 57 55
		f 3 -127 127 128
		mu 0 3 58 55 59
		f 3 -129 129 130
		mu 0 3 58 59 60
		f 3 131 132 -130
		mu 0 3 59 61 60
		f 3 -133 133 134
		mu 0 3 60 61 62
		f 3 135 136 -134
		mu 0 3 61 63 62
		f 3 -137 137 138
		mu 0 3 62 63 64
		f 3 139 140 -138
		mu 0 3 63 65 64
		f 3 -141 141 142
		mu 0 3 64 65 66
		f 3 143 144 -142
		mu 0 3 65 67 66
		f 3 -145 145 146
		mu 0 3 66 67 68
		f 3 147 148 -146
		mu 0 3 67 69 68
		f 3 149 150 -149
		mu 0 3 69 70 68
		f 3 151 -150 152
		mu 0 3 71 70 69
		f 3 153 -153 154
		mu 0 3 72 71 69
		f 3 155 -155 156
		mu 0 3 73 72 69
		f 3 157 -156 158
		mu 0 3 74 72 73
		f 3 -159 159 160
		mu 0 3 74 73 75
		f 3 161 -160 162
		mu 0 3 76 75 73
		f 3 163 164 -163
		mu 0 3 73 67 76
		f 3 165 -162 166
		mu 0 3 63 75 76
		f 3 167 168 -166
		mu 0 3 63 77 75
		f 3 -169 169 170
		mu 0 3 75 77 78
		f 3 171 -170 172
		mu 0 3 79 78 77
		f 3 173 -173 174
		mu 0 3 59 79 77
		f 3 175 -174 176
		mu 0 3 80 79 59
		f 3 -177 177 178
		mu 0 3 80 59 81
		f 3 179 -178 180
		mu 0 3 54 81 59
		f 3 181 182 -180
		mu 0 3 54 82 81
		f 3 183 -179 -183
		mu 0 3 82 80 81
		f 3 184 -184 185
		mu 0 3 83 80 82
		f 3 186 -186 187
		mu 0 3 84 83 82
		f 3 -188 188 189
		mu 0 3 84 82 85
		f 3 -189 190 191
		mu 0 3 85 82 51
		f 3 192 193 -192
		mu 0 3 51 47 85
		f 3 -194 194 195
		mu 0 3 85 47 86
		f 3 196 -195 197
		mu 0 3 87 86 47
		f 3 198 -198 199
		mu 0 3 88 87 47
		f 3 -200 200 201
		mu 0 3 88 47 89
		f 3 202 203 -202
		mu 0 3 89 90 88
		f 3 204 -204 205
		mu 0 3 91 88 90
		f 3 206 -206 207
		mu 0 3 92 91 90
		f 3 208 -208 209
		mu 0 3 93 92 90
		f 3 -210 210 211
		mu 0 3 93 90 94
		f 3 212 213 -211
		mu 0 3 90 95 94
		f 3 -214 214 215
		mu 0 3 94 95 96
		f 3 216 -216 217
		mu 0 3 97 94 96
		f 3 -218 218 219
		mu 0 3 97 96 98
		f 3 -220 220 221
		mu 0 3 97 98 99
		f 3 222 -222 223
		mu 0 3 100 97 99
		f 3 224 -224 225
		mu 0 3 101 100 99
		f 3 226 -226 227
		mu 0 3 102 101 99
		f 3 228 -228 229
		mu 0 3 103 102 99
		f 3 230 -230 231
		mu 0 3 104 103 99
		f 3 232 -231 233
		mu 0 3 27 103 104
		f 3 -229 -233 234
		mu 0 3 102 103 27
		f 3 235 236 -227
		mu 0 3 102 105 101
		f 3 237 -237 238
		mu 0 3 106 101 105
		f 3 239 240 -239
		mu 0 3 105 107 106
		f 3 -241 241 242
		mu 0 3 106 107 108
		f 3 -243 243 244
		mu 0 3 106 108 109
		f 3 245 246 -244
		mu 0 3 108 110 109
		f 3 247 -247 248
		mu 0 3 111 109 110
		f 3 249 -249 250
		mu 0 3 112 111 110
		f 3 251 -251 252
		mu 0 3 113 112 110
		f 3 253 -253 254
		mu 0 3 114 113 110
		f 3 -255 255 256
		mu 0 3 114 110 115
		f 3 257 -256 258
		mu 0 3 116 115 110
		f 3 259 260 -259
		mu 0 3 110 117 116
		f 3 261 -261 262
		mu 0 3 118 116 117
		f 3 263 -263 264
		mu 0 3 119 118 117
		f 3 -265 265 266
		mu 0 3 119 117 120
		f 3 -267 267 268
		mu 0 3 119 120 121
		f 3 269 -269 270
		mu 0 3 122 119 121
		f 3 271 272 -271
		mu 0 3 121 123 122
		f 3 -273 273 274
		mu 0 3 122 123 124
		f 3 275 -275 276
		mu 0 3 125 122 124
		f 3 -277 277 278
		mu 0 3 125 124 126
		f 3 279 280 -279
		mu 0 3 126 127 125
		f 3 281 282 -281
		mu 0 3 127 128 125
		f 3 283 284 -283
		mu 0 3 128 129 125
		f 3 285 286 -284
		mu 0 3 128 118 129
		f 3 287 288 -286
		mu 0 3 128 130 118
		f 3 289 -289 290
		mu 0 3 131 118 130
		f 3 -291 291 292
		mu 0 3 131 130 132
		f 3 293 294 -293
		mu 0 3 132 133 131
		f 3 295 296 -295
		mu 0 3 133 115 131
		f 3 297 298 -296
		mu 0 3 133 134 115
		f 3 -299 299 300
		mu 0 3 115 134 135
		f 3 301 302 -300
		mu 0 3 134 136 135
		f 3 303 304 -303
		mu 0 3 136 137 135
		f 3 -305 305 306
		mu 0 3 135 137 138
		f 3 307 -306 308
		mu 0 3 139 138 137
		f 3 -308 309 310
		mu 0 3 138 139 140
		f 3 311 -311 312
		mu 0 3 141 138 140
		f 3 313 314 -313
		mu 0 3 140 142 141
		f 3 315 316 -315
		mu 0 3 142 143 141
		f 3 317 -317 318
		mu 0 3 144 141 143
		f 3 -319 319 320
		mu 0 3 144 143 145
		f 3 321 322 -321
		mu 0 3 145 146 144
		f 3 323 -323 324
		mu 0 3 147 144 146
		f 3 325 326 -325
		mu 0 3 146 148 147
		f 3 -327 327 328
		mu 0 3 147 148 149
		f 3 329 330 -328
		mu 0 3 148 150 149
		f 3 -331 331 332
		mu 0 3 149 150 151
		f 3 -333 333 334
		mu 0 3 149 151 152
		f 3 -334 335 336
		mu 0 3 152 151 153
		f 3 337 -337 338
		mu 0 3 154 152 153
		f 3 -339 339 340
		mu 0 3 154 153 155
		f 3 341 342 -340
		mu 0 3 153 156 155
		f 3 343 -343 344
		mu 0 3 157 155 156
		f 3 345 346 -345
		mu 0 3 156 158 157
		f 3 347 -347 348
		mu 0 3 159 157 158
		f 3 -349 349 350
		mu 0 3 159 158 160
		f 3 351 -351 352
		mu 0 3 161 159 160
		f 3 -353 353 354
		mu 0 3 161 160 162
		f 3 355 -354 356
		mu 0 3 163 162 160
		f 3 -357 357 358
		mu 0 3 163 160 164
		f 3 359 360 -359
		mu 0 3 164 165 163
		f 3 361 -361 362
		mu 0 3 166 163 165
		f 3 -363 363 364
		mu 0 3 166 165 167
		f 3 365 366 -365
		mu 0 3 167 168 166
		f 3 367 -367 368
		mu 0 3 169 166 168
		f 3 369 -369 370
		mu 0 3 170 169 168
		f 3 371 -371 372
		mu 0 3 171 170 168
		f 3 373 374 -372
		mu 0 3 171 172 170
		f 3 -375 375 376
		mu 0 3 170 172 173
		f 3 377 -377 378
		mu 0 3 174 170 173
		f 3 379 -379 380
		mu 0 3 175 174 173
		f 3 381 382 -381
		mu 0 3 173 176 175
		f 3 383 384 -383
		mu 0 3 176 177 175
		f 3 -385 385 386
		mu 0 3 175 177 178
		f 3 387 -387 388
		mu 0 3 179 175 178
		f 3 389 -389 390
		mu 0 3 180 179 178
		f 3 391 -391 392
		mu 0 3 181 180 178
		f 3 393 394 -392
		mu 0 3 181 182 180
		f 3 395 -395 396
		mu 0 3 183 180 182
		f 3 397 -397 398
		mu 0 3 184 183 182
		f 3 -399 399 400
		mu 0 3 184 182 185
		f 3 401 -401 402
		mu 0 3 186 184 185
		f 3 403 -403 404
		mu 0 3 187 186 185
		f 3 405 -404 406
		mu 0 3 188 186 187
		f 3 407 408 -407
		mu 0 3 187 189 188
		f 3 409 410 -409
		mu 0 3 189 190 188
		f 3 411 -411 412
		mu 0 3 191 188 190
		f 3 -413 413 414
		mu 0 3 191 190 192
		f 3 -415 415 416
		mu 0 3 191 192 193
		f 3 417 418 -417
		mu 0 3 193 194 191
		f 3 419 -419 420
		mu 0 3 195 191 194
		f 3 421 422 -421
		mu 0 3 194 196 195
		f 3 423 -423 424
		mu 0 3 197 195 196
		f 3 425 426 -425
		mu 0 3 196 198 197
		f 3 -427 427 428
		mu 0 3 197 198 199
		f 3 429 430 -428
		mu 0 3 198 184 199
		f 3 431 432 -430
		mu 0 3 198 200 184
		f 3 433 434 -432
		mu 0 3 198 201 200
		f 3 435 436 -435
		mu 0 3 201 202 200
		f 3 -437 437 438
		mu 0 3 200 202 203
		f 3 -438 439 440
		mu 0 3 203 202 204
		f 3 441 442 -441
		mu 0 3 204 205 203
		f 3 443 444 -443
		mu 0 3 205 206 203
		f 3 -445 445 446
		mu 0 3 203 206 207
		f 3 -446 447 448
		mu 0 3 207 206 208
		f 3 449 450 -448
		mu 0 3 206 209 208
		f 3 451 452 -451
		mu 0 3 209 210 208
		f 3 -453 453 454
		mu 0 3 208 210 211
		f 3 455 -454 456
		mu 0 3 212 211 210
		f 3 457 -457 458
		mu 0 3 213 212 210
		f 3 -459 459 460
		mu 0 3 213 210 214
		f 3 461 -460 462
		mu 0 3 215 214 210
		f 3 463 464 -463
		mu 0 3 210 216 215
		f 3 465 -465 466
		mu 0 3 217 215 216
		f 3 467 -467 468
		mu 0 3 205 217 216
		f 3 469 470 -468
		mu 0 3 205 218 217
		f 3 471 472 -471
		mu 0 3 218 219 217
		f 3 -472 473 474
		mu 0 3 219 218 220
		f 3 -474 475 476
		mu 0 3 220 218 221
		f 3 477 478 -477
		mu 0 3 221 222 220
		f 3 479 -479 480
		mu 0 3 223 220 222
		f 3 481 482 -481
		mu 0 3 222 224 223
		f 3 483 -483 484
		mu 0 3 225 223 224
		f 3 485 -485 486
		mu 0 3 226 225 224
		f 3 487 -487 488
		mu 0 3 227 226 224
		f 3 -489 489 490
		mu 0 3 227 224 221
		f 3 491 -491 492
		mu 0 3 228 227 221
		f 3 493 -493 494
		mu 0 3 229 228 221
		f 3 -495 495 496
		mu 0 3 229 221 230
		f 3 497 -497 498
		mu 0 3 202 229 230
		f 3 499 -494 500
		mu 0 3 231 228 229
		f 3 501 -501 502
		mu 0 3 232 231 229
		f 3 503 -503 504
		mu 0 3 201 232 229
		f 3 505 -504 506
		mu 0 3 233 232 201
		f 3 507 -507 508
		mu 0 3 196 233 201
		f 3 509 510 -506
		mu 0 3 233 234 232
		f 3 511 512 -511
		mu 0 3 234 235 232
		f 3 513 514 -513
		mu 0 3 235 236 232
		f 3 515 516 -514
		mu 0 3 235 237 236
		f 3 -517 517 518
		mu 0 3 236 237 238
		f 3 -519 519 520
		mu 0 3 236 238 231
		f 3 -520 521 522
		mu 0 3 231 238 239
		f 3 523 524 -522
		mu 0 3 238 240 239
		f 3 525 526 -525
		mu 0 3 240 241 239
		f 3 527 528 -527
		mu 0 3 241 227 239
		f 3 529 530 -526
		mu 0 3 240 242 241
		f 3 531 532 -531
		mu 0 3 242 243 241
		f 3 533 534 -533
		mu 0 3 243 226 241
		f 3 -532 535 536
		mu 0 3 243 242 244
		f 3 537 538 -536
		mu 0 3 242 245 244
		f 3 -539 539 540
		mu 0 3 244 245 246
		f 3 -540 541 542
		mu 0 3 246 245 247
		f 3 543 544 -543
		mu 0 3 247 248 246
		f 3 545 546 -545
		mu 0 3 248 249 246
		f 3 -547 547 548
		mu 0 3 246 249 250
		f 3 -548 549 550
		mu 0 3 250 249 251
		f 3 -551 551 552
		mu 0 3 250 251 252
		f 3 -552 553 554
		mu 0 3 252 251 253
		f 3 -555 555 556
		mu 0 3 252 253 254
		f 3 -556 557 558
		mu 0 3 254 253 255
		f 3 559 -559 560
		mu 0 3 256 254 255
		f 3 561 562 -561
		mu 0 3 255 257 256
		f 3 563 564 -563
		mu 0 3 257 258 256
		f 3 565 566 -565
		mu 0 3 258 259 256
		f 3 567 568 -566
		mu 0 3 258 260 259
		f 3 -569 569 570
		mu 0 3 259 260 254
		f 3 571 572 -570
		mu 0 3 260 261 254
		f 3 573 -573 574
		mu 0 3 262 254 261
		f 3 -575 575 576
		mu 0 3 262 261 263
		f 3 577 -576 578
		mu 0 3 264 263 261
		f 3 579 580 -579
		mu 0 3 261 265 264
		f 3 -581 581 582
		mu 0 3 264 265 266
		f 3 -582 583 584
		mu 0 3 266 265 267
		f 3 585 586 -584
		mu 0 3 265 258 267
		f 3 -585 587 588
		mu 0 3 266 267 268
		f 3 589 -589 590
		mu 0 3 269 266 268
		f 3 -591 591 592
		mu 0 3 269 268 270
		f 3 593 594 -592
		mu 0 3 268 271 270
		f 3 595 -595 596
		mu 0 3 272 270 271
		f 3 597 -597 598
		mu 0 3 273 272 271
		f 3 599 -598 600
		mu 0 3 274 272 273
		f 3 601 -601 602
		mu 0 3 275 274 273
		f 3 603 -603 604
		mu 0 3 276 275 273
		f 3 -605 605 606
		mu 0 3 276 273 277
		f 3 -607 607 608
		mu 0 3 276 277 278
		f 3 -608 609 610
		mu 0 3 278 277 279
		f 3 -611 611 612
		mu 0 3 278 279 280
		f 3 -613 613 614
		mu 0 3 278 280 281
		f 3 -615 615 616
		mu 0 3 278 281 282
		f 3 617 618 -616
		mu 0 3 281 283 282
		f 3 619 620 -619
		mu 0 3 283 284 282
		f 3 -621 621 622
		mu 0 3 282 284 276
		f 3 623 624 -620
		mu 0 3 283 285 284
		f 3 625 626 -625
		mu 0 3 285 286 284
		f 3 627 628 -627
		mu 0 3 286 287 284
		f 3 629 -629 630
		mu 0 3 288 284 287
		f 3 -631 631 632
		mu 0 3 288 287 289
		f 3 633 634 -633
		mu 0 3 289 290 288
		f 3 635 636 -635
		mu 0 3 290 291 288
		f 3 637 -637 638
		mu 0 3 274 288 291
		f 3 639 640 -636
		mu 0 3 290 292 291
		f 3 641 -641 642
		mu 0 3 293 291 292
		f 3 643 -643 644
		mu 0 3 294 293 292
		f 3 -645 645 646
		mu 0 3 294 292 295
		f 3 -646 647 648
		mu 0 3 295 292 296
		f 3 -649 649 650
		mu 0 3 295 296 297
		f 3 651 652 -650
		mu 0 3 296 298 297
		f 3 653 -653 654
		mu 0 3 299 297 298
		f 3 -655 655 656
		mu 0 3 299 298 289
		f 3 -654 657 658
		mu 0 3 297 299 300
		f 3 659 -659 660
		mu 0 3 301 297 300
		f 3 -661 661 662
		mu 0 3 301 300 302
		f 3 -663 663 664
		mu 0 3 301 302 303
		f 3 665 -665 666
		mu 0 3 304 301 303
		f 3 667 -667 668
		mu 0 3 305 304 303
		f 3 -669 669 670
		mu 0 3 305 303 306
		f 3 671 -671 672
		mu 0 3 307 305 306
		f 3 -673 673 674
		mu 0 3 307 306 308
		f 3 675 -675 676
		mu 0 3 309 307 308
		f 3 677 678 -677
		mu 0 3 308 310 309
		f 3 -679 679 680
		mu 0 3 309 310 311
		f 3 -680 681 682
		mu 0 3 311 310 312
		f 3 -683 683 684
		mu 0 3 311 312 313
		f 3 685 -685 686
		mu 0 3 314 311 313
		f 3 -687 687 688
		mu 0 3 314 313 315
		f 3 -689 689 690
		mu 0 3 314 315 316
		f 3 691 -691 692
		mu 0 3 317 314 316
		f 3 693 -693 694
		mu 0 3 318 317 316
		f 3 695 696 -695
		mu 0 3 316 319 318
		f 3 697 -697 698
		mu 0 3 320 318 319
		f 3 -699 699 700
		mu 0 3 320 319 321
		f 3 701 702 -700
		mu 0 3 319 322 321
		f 3 703 704 -703
		mu 0 3 322 323 321
		f 3 705 -705 706
		mu 0 3 324 321 323
		f 3 -707 707 708
		mu 0 3 324 323 325
		f 3 709 -709 710
		mu 0 3 326 324 325
		f 3 711 712 -711
		mu 0 3 325 327 326
		f 3 -713 713 714
		mu 0 3 326 327 328
		f 3 715 -715 716
		mu 0 3 329 326 328
		f 3 717 -717 718
		mu 0 3 320 329 328
		f 3 -719 719 720
		mu 0 3 320 328 330
		f 3 721 -720 722
		mu 0 3 331 330 328
		f 3 723 -723 724
		mu 0 3 332 331 328
		f 3 725 726 -725
		mu 0 3 328 333 332
		f 3 -727 727 728
		mu 0 3 332 333 334
		f 3 729 -729 730
		mu 0 3 335 332 334
		f 3 731 -731 732
		mu 0 3 336 335 334
		f 3 733 734 -733
		mu 0 3 334 337 336
		f 3 -735 735 736
		mu 0 3 336 337 338
		f 3 -736 737 738
		mu 0 3 338 337 339
		f 3 739 740 -739
		mu 0 3 339 340 338
		f 3 741 -741 742
		mu 0 3 341 338 340
		f 3 -743 743 744
		mu 0 3 341 340 342
		f 3 745 -745 746
		mu 0 3 343 341 342
		f 3 -747 747 748
		mu 0 3 343 342 344
		f 3 -748 749 750
		mu 0 3 344 342 345
		f 3 -750 751 752
		mu 0 3 345 342 346
		f 3 753 754 -752
		mu 0 3 342 347 346
		f 3 -755 755 756
		mu 0 3 346 347 348
		f 3 -756 757 758
		mu 0 3 348 347 349
		f 3 759 760 -758
		mu 0 3 347 350 349
		f 3 -761 761 762
		mu 0 3 349 350 351
		f 3 763 -762 764
		mu 0 3 352 351 350
		f 3 -765 765 766
		mu 0 3 352 350 353
		f 3 767 768 -766
		mu 0 3 350 354 353
		f 3 769 770 -769
		mu 0 3 354 355 353
		f 3 -771 771 772
		mu 0 3 353 355 356
		f 3 773 774 -772
		mu 0 3 355 357 356
		f 3 775 776 -775
		mu 0 3 357 358 356
		f 3 -777 777 778
		mu 0 3 356 358 359
		f 3 779 -779 780
		mu 0 3 352 356 359
		f 3 781 -781 782
		mu 0 3 360 352 359
		f 3 -783 783 784
		mu 0 3 360 359 361
		f 3 785 -784 786
		mu 0 3 362 361 359
		f 3 787 788 -787
		mu 0 3 359 363 362
		f 3 789 790 -789
		mu 0 3 363 364 362
		f 3 -791 791 792
		mu 0 3 362 364 365
		f 3 793 794 -792
		mu 0 3 364 366 365
		f 3 -794 795 796
		mu 0 3 366 364 367
		f 3 -797 797 798
		mu 0 3 366 367 368
		f 3 799 -799 800
		mu 0 3 369 366 368
		f 3 801 -801 802
		mu 0 3 370 369 368
		f 3 -803 803 804
		mu 0 3 370 368 371
		f 3 805 806 -805
		mu 0 3 371 372 370
		f 3 807 808 -806
		mu 0 3 371 373 372
		f 3 809 -809 810
		mu 0 3 374 372 373
		f 3 811 812 -811
		mu 0 3 373 375 374
		f 3 813 814 -813
		mu 0 3 375 376 374
		f 3 815 -815 816
		mu 0 3 377 374 376
		f 3 817 -817 818
		mu 0 3 378 377 376
		f 3 819 820 -819
		mu 0 3 376 379 378
		f 3 -821 821 822
		mu 0 3 378 379 380
		f 3 823 824 -823
		mu 0 3 380 381 378
		f 3 -824 825 826
		mu 0 3 381 380 382
		f 3 827 -826 -822
		mu 0 3 379 382 380
		f 3 828 829 -828
		mu 0 3 379 383 382
		f 3 -830 830 831
		mu 0 3 382 383 384
		f 3 -832 832 833
		mu 0 3 382 384 385
		f 3 834 835 -833
		mu 0 3 384 386 385
		f 3 836 -836 837
		mu 0 3 387 385 386
		f 3 838 839 -838
		mu 0 3 386 388 387
		f 3 840 -840 841
		mu 0 3 389 387 388
		f 3 842 -842 843
		mu 0 3 390 389 388
		f 3 844 -844 845
		mu 0 3 391 390 388
		f 3 846 -846 847
		mu 0 3 392 391 388
		f 3 848 -848 849
		mu 0 3 393 392 388
		f 3 850 -850 851
		mu 0 3 394 393 388
		f 3 852 -852 853
		mu 0 3 395 394 388
		f 3 854 -854 855
		mu 0 3 396 395 388
		f 3 856 -856 857
		mu 0 3 397 396 388
		f 3 858 859 -857
		mu 0 3 397 398 396
		f 3 860 -860 861
		mu 0 3 399 396 398
		f 3 -862 862 863
		mu 0 3 399 398 383
		f 3 864 865 -864
		mu 0 3 383 400 399
		f 3 866 867 -866
		mu 0 3 400 401 399
		f 3 -868 868 869
		mu 0 3 399 401 402
		f 3 -869 870 871
		mu 0 3 402 401 403
		f 3 872 873 -872
		mu 0 3 403 404 402
		f 3 -874 874 875
		mu 0 3 402 404 405
		f 3 -876 876 877
		mu 0 3 402 405 395
		f 3 -877 878 879
		mu 0 3 395 405 406
		f 3 880 881 -879
		mu 0 3 405 407 406
		f 3 882 883 -882
		mu 0 3 407 408 406
		f 3 -884 884 885
		mu 0 3 406 408 409
		f 3 886 887 -885
		mu 0 3 408 410 409
		f 3 -888 888 889
		mu 0 3 409 410 392
		f 3 890 891 -887
		mu 0 3 408 411 410
		f 3 892 -892 893
		mu 0 3 412 410 411
		f 3 -894 894 895
		mu 0 3 412 411 413
		f 3 -896 896 897
		mu 0 3 412 413 414
		f 3 898 -898 899
		mu 0 3 389 412 414
		f 3 900 -900 901
		mu 0 3 415 389 414
		f 3 902 903 -902
		mu 0 3 414 416 415
		f 3 904 905 -903
		mu 0 3 414 417 416
		f 3 -905 906 907
		mu 0 3 417 414 418
		f 3 -908 908 909
		mu 0 3 417 418 419
		f 3 910 911 -909
		mu 0 3 418 420 419
		f 3 -912 912 913
		mu 0 3 419 420 421
		f 3 914 915 -913
		mu 0 3 420 422 421
		f 3 -916 916 917
		mu 0 3 421 422 423
		f 3 -918 918 919
		mu 0 3 421 423 424
		f 3 920 921 -919
		mu 0 3 423 425 424
		f 3 922 -922 923
		mu 0 3 426 424 425
		f 3 924 -924 925
		mu 0 3 427 426 425
		f 3 926 -926 927
		mu 0 3 428 427 425
		f 3 928 929 -928
		mu 0 3 425 429 428
		f 3 930 -930 931
		mu 0 3 430 428 429
		f 3 932 933 -932
		mu 0 3 429 431 430
		f 3 934 935 -934
		mu 0 3 431 432 430
		f 3 936 -936 937
		mu 0 3 433 430 432
		f 3 938 939 -938
		mu 0 3 432 434 433
		f 3 940 941 -940
		mu 0 3 434 435 433
		f 3 -942 942 943
		mu 0 3 433 435 436
		f 3 -944 944 945
		mu 0 3 433 436 437
		f 3 -946 946 947
		mu 0 3 433 437 438
		f 3 948 -947 949
		mu 0 3 428 438 437
		f 3 -950 950 951
		mu 0 3 428 437 439
		f 3 952 953 -945
		mu 0 3 436 440 437
		f 3 954 955 -954
		mu 0 3 440 441 437
		f 3 956 957 -955
		mu 0 3 440 442 441
		f 3 -958 958 959
		mu 0 3 441 442 443
		f 3 960 961 -959
		mu 0 3 442 444 443
		f 3 -961 962 963
		mu 0 3 444 442 445
		f 3 -963 964 965
		mu 0 3 445 442 446
		f 3 966 967 -966
		mu 0 3 446 447 445
		f 3 968 -967 969
		mu 0 3 448 447 446
		f 3 -970 970 971
		mu 0 3 448 446 449
		f 3 972 973 -972
		mu 0 3 449 450 448
		f 3 -974 974 975
		mu 0 3 448 450 451
		f 3 976 977 -975
		mu 0 3 450 452 451
		f 3 978 979 -978
		mu 0 3 452 453 451
		f 3 980 981 -980
		mu 0 3 453 454 451
		f 3 982 -981 983
		mu 0 3 455 454 453
		f 3 -984 984 985
		mu 0 3 455 453 456
		f 3 986 987 -985
		mu 0 3 453 457 456
		f 3 988 989 -988
		mu 0 3 457 458 456
		f 3 990 991 -990
		mu 0 3 458 459 456
		f 3 992 993 -992
		mu 0 3 459 460 456
		f 3 994 -994 995
		mu 0 3 461 456 460
		f 3 -996 996 997
		mu 0 3 461 460 462;
	setAttr ".fc[500:999]"
		f 3 998 -998 999
		mu 0 3 463 461 462
		f 3 1000 -1000 1001
		mu 0 3 464 463 462
		f 3 -1002 1002 1003
		mu 0 3 464 462 465
		f 3 1004 1005 -1001
		mu 0 3 464 466 463
		f 3 -1006 1006 1007
		mu 0 3 463 466 467
		f 3 1008 1009 -1007
		mu 0 3 466 468 467
		f 3 -1010 1010 1011
		mu 0 3 467 468 469
		f 3 -1011 1012 1013
		mu 0 3 469 468 470
		f 3 1014 1015 -1014
		mu 0 3 470 471 469
		f 3 1016 1017 -1016
		mu 0 3 471 472 469
		f 3 -1018 1018 1019
		mu 0 3 469 472 473
		f 3 -1019 1020 1021
		mu 0 3 473 472 474
		f 3 1022 1023 -1022
		mu 0 3 474 455 473
		f 3 -1023 1024 1025
		mu 0 3 455 474 475
		f 3 1026 1027 -1015
		mu 0 3 470 476 471
		f 3 1028 1029 -1027
		mu 0 3 470 477 476
		f 3 -1029 1030 1031
		mu 0 3 477 470 478
		f 3 1032 -1032 1033
		mu 0 3 479 477 478
		f 3 1034 -1034 1035
		mu 0 3 480 479 478
		f 3 -1036 1036 1037
		mu 0 3 480 478 481
		f 3 1038 1039 -1037
		mu 0 3 478 468 481
		f 3 1040 1041 -1040
		mu 0 3 468 482 481
		f 3 1042 -1041 1043
		mu 0 3 483 482 468
		f 3 -1013 -1039 -1031
		mu 0 3 470 468 478
		f 3 -1012 -1020 1044
		mu 0 3 467 469 473
		f 3 -1045 1045 1046
		mu 0 3 467 473 461
		f 3 -1044 -1009 1047
		mu 0 3 483 468 466
		f 3 -1008 -1047 -999
		mu 0 3 463 467 461
		f 3 -997 1048 -1003
		mu 0 3 462 460 465
		f 3 1049 -995 -1046
		mu 0 3 473 456 461
		f 3 -993 1050 -1049
		mu 0 3 460 459 465
		f 3 1051 -1051 1052
		mu 0 3 484 465 459
		f 3 -1053 1053 1054
		mu 0 3 484 459 485
		f 3 1055 -1055 1056
		mu 0 3 486 484 485
		f 3 1057 -1057 1058
		mu 0 3 487 486 485
		f 3 1059 -1059 1060
		mu 0 3 488 487 485
		f 3 -1061 1061 1062
		mu 0 3 488 485 489
		f 3 1063 -1062 1064
		mu 0 3 490 489 485
		f 3 -1054 1065 -1065
		mu 0 3 485 459 490
		f 3 -1066 1066 1067
		mu 0 3 490 459 491
		f 3 -1067 -991 1068
		mu 0 3 491 459 458
		f 3 -1069 1069 1070
		mu 0 3 491 458 492
		f 3 1071 -1071 1072
		mu 0 3 493 491 492
		f 3 1073 -1073 1074
		mu 0 3 494 493 492
		f 3 -1075 1075 1076
		mu 0 3 494 492 495
		f 3 -1076 1077 1078
		mu 0 3 495 492 496
		f 3 1079 -1079 1080
		mu 0 3 497 495 496
		f 3 -1081 1081 1082
		mu 0 3 497 496 498
		f 3 -1082 1083 1084
		mu 0 3 498 496 499
		f 3 1085 -1084 1086
		mu 0 3 500 499 496
		f 3 1087 -1087 1088
		mu 0 3 501 500 496
		f 3 1089 1090 -1089
		mu 0 3 496 458 501
		f 3 1091 1092 -1088
		mu 0 3 501 502 500
		f 3 -1092 1093 1094
		mu 0 3 502 501 457
		f 3 1095 -1095 1096
		mu 0 3 452 502 457
		f 3 1097 -1086 -1093
		mu 0 3 502 499 500
		f 3 -1098 1098 1099
		mu 0 3 499 502 450
		f 3 -1100 1100 1101
		mu 0 3 499 450 503
		f 3 1102 1103 -1101
		mu 0 3 450 504 503
		f 3 1104 -1104 1105
		mu 0 3 498 503 504
		f 3 -1102 -1105 -1085
		mu 0 3 499 503 498
		f 3 1106 -1077 -1080
		mu 0 3 497 494 495
		f 3 -1070 -1090 -1078
		mu 0 3 492 458 496
		f 3 -1094 -1091 -989
		mu 0 3 457 501 458
		f 3 -1024 -986 -1050
		mu 0 3 473 455 456
		f 3 -1026 1107 -983
		mu 0 3 455 475 454
		f 3 1108 -1108 1109
		mu 0 3 448 454 475
		f 3 -1097 -987 -979
		mu 0 3 452 457 453
		f 3 -1099 -1096 -977
		mu 0 3 450 502 452
		f 3 -976 -982 -1109
		mu 0 3 448 451 454
		f 3 1110 -1103 -973
		mu 0 3 449 504 450
		f 3 -1111 1111 1112
		mu 0 3 504 449 505
		f 3 1113 -1112 1114
		mu 0 3 506 505 449
		f 3 1115 -1115 1116
		mu 0 3 507 506 449
		f 3 -1116 1117 1118
		mu 0 3 506 507 508
		f 3 1119 -1119 1120
		mu 0 3 509 506 508
		f 3 1121 -1121 1122
		mu 0 3 510 509 508
		f 3 -1123 1123 1124
		mu 0 3 510 508 511
		f 3 1125 -1124 1126
		mu 0 3 512 511 508
		f 3 1127 -1126 1128
		mu 0 3 513 511 512
		f 3 1129 -1129 1130
		mu 0 3 514 513 512
		f 3 1131 -1131 1132
		mu 0 3 507 514 512
		f 3 1133 -1132 1134
		mu 0 3 515 514 507
		f 3 1135 -1135 1136
		mu 0 3 446 515 507
		f 3 1137 1138 -1136
		mu 0 3 446 516 515
		f 3 1139 -1139 1140
		mu 0 3 517 515 516
		f 3 1141 1142 -1141
		mu 0 3 516 518 517
		f 3 1143 1144 -1143
		mu 0 3 518 519 517
		f 3 1145 1146 -1145
		mu 0 3 519 514 517
		f 3 1147 1148 -1146
		mu 0 3 519 520 514
		f 3 1149 1150 -1149
		mu 0 3 520 521 514
		f 3 1151 -1150 1152
		mu 0 3 522 521 520
		f 3 1153 1154 -1153
		mu 0 3 520 523 522
		f 3 1155 1156 -1155
		mu 0 3 523 524 522
		f 3 1157 1158 -1157
		mu 0 3 524 525 522
		f 3 1159 -1159 1160
		mu 0 3 526 522 525
		f 3 1161 -1161 1162
		mu 0 3 527 526 525
		f 3 1163 1164 -1163
		mu 0 3 525 528 527
		f 3 1165 1166 -1165
		mu 0 3 528 529 527
		f 3 1167 -1167 1168
		mu 0 3 530 527 529
		f 3 1169 1170 -1169
		mu 0 3 529 531 530
		f 3 1171 1172 -1171
		mu 0 3 531 532 530
		f 3 -1173 1173 1174
		mu 0 3 530 532 533
		f 3 -1175 1175 1176
		mu 0 3 530 533 534
		f 3 1177 -1176 1178
		mu 0 3 535 534 533
		f 3 -1179 1179 1180
		mu 0 3 535 533 536
		f 3 -1181 1181 1182
		mu 0 3 535 536 537
		f 3 1183 1184 -1183
		mu 0 3 537 538 535
		f 3 1185 -1184 1186
		mu 0 3 539 538 537
		f 3 1187 -1187 1188
		mu 0 3 540 539 537
		f 3 -1189 1189 1190
		mu 0 3 540 537 541
		f 3 1191 -1190 1192
		mu 0 3 542 541 537
		f 3 1193 1194 -1192
		mu 0 3 542 543 541
		f 3 1195 -1195 1196
		mu 0 3 544 541 543
		f 3 1197 1198 -1196
		mu 0 3 544 545 541
		f 3 -1194 1199 1200
		mu 0 3 543 542 546
		f 3 -1201 1201 1202
		mu 0 3 543 546 547
		f 3 -1202 1203 1204
		mu 0 3 547 546 548
		f 3 1205 -1204 1206
		mu 0 3 549 548 546
		f 3 1207 1208 -1207
		mu 0 3 546 550 549
		f 3 1209 1210 -1209
		mu 0 3 550 551 549
		f 3 1211 1212 -1211
		mu 0 3 551 552 549
		f 3 -1212 1213 1214
		mu 0 3 552 551 553
		f 3 -1215 1215 1216
		mu 0 3 552 553 554
		f 3 1217 -1216 1218
		mu 0 3 555 554 553
		f 3 1219 -1219 1220
		mu 0 3 556 555 553
		f 3 1221 -1220 1222
		mu 0 3 557 555 556
		f 3 1223 -1223 1224
		mu 0 3 551 557 556
		f 3 1225 1226 -1224
		mu 0 3 551 558 557
		f 3 1227 -1227 1228
		mu 0 3 532 557 558
		f 3 1229 1230 -1228
		mu 0 3 532 559 557
		f 3 1231 1232 -1230
		mu 0 3 532 560 559
		f 3 -1233 1233 1234
		mu 0 3 559 560 561
		f 3 1235 1236 -1234
		mu 0 3 560 562 561
		f 3 1237 1238 -1237
		mu 0 3 562 563 561
		f 3 -1239 1239 1240
		mu 0 3 561 563 564
		f 3 -1240 1241 1242
		mu 0 3 564 563 565
		f 3 -1243 1243 1244
		mu 0 3 564 565 566
		f 3 1245 1246 -1245
		mu 0 3 566 567 564
		f 3 -1247 1247 1248
		mu 0 3 564 567 568
		f 3 -1249 1249 1250
		mu 0 3 564 568 569
		f 3 1251 -1250 1252
		mu 0 3 570 569 568
		f 3 1253 -1253 1254
		mu 0 3 571 570 568
		f 3 1255 1256 -1255
		mu 0 3 568 572 571
		f 3 -1257 1257 1258
		mu 0 3 571 572 573
		f 3 1259 -1259 1260
		mu 0 3 554 571 573
		f 3 -1261 1261 1262
		mu 0 3 554 573 574
		f 3 1263 -1263 1264
		mu 0 3 575 554 574
		f 3 1265 -1265 1266
		mu 0 3 576 575 574
		f 3 1267 1268 -1267
		mu 0 3 574 577 576
		f 3 1269 1270 -1269
		mu 0 3 577 578 576
		f 3 1271 1272 -1270
		mu 0 3 577 579 578
		f 3 1273 1274 -1273
		mu 0 3 579 580 578
		f 3 -1274 1275 1276
		mu 0 3 580 579 581
		f 3 -1277 1277 1278
		mu 0 3 580 581 582
		f 3 1279 1280 -1278
		mu 0 3 581 583 582
		f 3 1281 -1281 1282
		mu 0 3 584 582 583
		f 3 -1283 1283 1284
		mu 0 3 584 583 585
		f 3 -1284 1285 1286
		mu 0 3 585 583 586
		f 3 -1287 1287 1288
		mu 0 3 585 586 587
		f 3 1289 1290 -1288
		mu 0 3 586 588 587
		f 3 1291 1292 -1291
		mu 0 3 588 589 587
		f 3 1293 1294 -1293
		mu 0 3 589 590 587
		f 3 -1295 1295 1296
		mu 0 3 587 590 591
		f 3 1297 -1296 1298
		mu 0 3 592 591 590
		f 3 1299 -1299 1300
		mu 0 3 593 592 590
		f 3 1301 1302 -1300
		mu 0 3 593 594 592
		f 3 1303 -1303 1304
		mu 0 3 595 592 594
		f 3 -1305 1305 1306
		mu 0 3 595 594 596
		f 3 1307 -1307 1308
		mu 0 3 597 595 596
		f 3 1309 1310 -1309
		mu 0 3 596 598 597
		f 3 1311 1312 -1311
		mu 0 3 598 599 597
		f 3 1313 1314 -1313
		mu 0 3 599 600 597
		f 3 1315 1316 -1315
		mu 0 3 600 601 597
		f 3 1317 1318 -1317
		mu 0 3 601 602 597
		f 3 1319 1320 -1319
		mu 0 3 602 603 597
		f 3 1321 -1321 1322
		mu 0 3 587 597 603
		f 3 1323 -1323 1324
		mu 0 3 604 587 603
		f 3 -1325 -1320 1325
		mu 0 3 604 603 602
		f 3 -1326 1326 1327
		mu 0 3 604 602 605
		f 3 1328 1329 -1328
		mu 0 3 605 584 604
		f 3 1330 1331 -1316
		mu 0 3 600 606 601
		f 3 -1331 -1314 1332
		mu 0 3 606 600 599
		f 3 1333 1334 -1333
		mu 0 3 599 607 606
		f 3 1335 -1334 1336
		mu 0 3 608 607 599
		f 3 1337 -1337 1338
		mu 0 3 609 608 599
		f 3 1339 1340 -1339
		mu 0 3 599 610 609
		f 3 1341 1342 -1341
		mu 0 3 610 611 609
		f 3 -1342 1343 1344
		mu 0 3 611 610 612
		f 3 -1344 1345 1346
		mu 0 3 612 610 613
		f 3 1347 -1346 1348
		mu 0 3 614 613 610
		f 3 1349 1350 -1349
		mu 0 3 610 615 614
		f 3 1351 1352 -1351
		mu 0 3 615 616 614
		f 3 -1353 1353 1354
		mu 0 3 614 616 617
		f 3 -1355 1355 1356
		mu 0 3 614 617 618
		f 3 1357 1358 -1356
		mu 0 3 617 619 618
		f 3 -1359 1359 1360
		mu 0 3 618 619 613
		f 3 1361 -1360 1362
		mu 0 3 620 613 619
		f 3 1363 -1363 1364
		mu 0 3 621 620 619
		f 3 1365 -1365 1366
		mu 0 3 622 621 619
		f 3 -1367 1367 1368
		mu 0 3 622 619 623
		f 3 1369 -1369 1370
		mu 0 3 624 622 623
		f 3 -1371 1371 1372
		mu 0 3 624 623 625
		f 3 1373 -1373 1374
		mu 0 3 626 624 625
		f 3 -1375 1375 1376
		mu 0 3 626 625 627
		f 3 1377 1378 -1377
		mu 0 3 627 628 626
		f 3 1379 1380 -1378
		mu 0 3 627 629 628
		f 3 1381 -1381 1382
		mu 0 3 630 628 629
		f 3 -1383 1383 1384
		mu 0 3 630 629 631
		f 3 1385 -1385 1386
		mu 0 3 632 630 631
		f 3 1387 -1387 1388
		mu 0 3 633 632 631
		f 3 -1389 1389 1390
		mu 0 3 633 631 634
		f 3 -1390 1391 1392
		mu 0 3 634 631 635
		f 3 -1393 1393 1394
		mu 0 3 634 635 636
		f 3 1395 1396 -1394
		mu 0 3 635 637 636
		f 3 -1397 1397 1398
		mu 0 3 636 637 638
		f 3 1399 1400 -1398
		mu 0 3 637 639 638
		f 3 -1401 1401 1402
		mu 0 3 638 639 640
		f 3 1403 -1402 1404
		mu 0 3 641 640 639
		f 3 1405 1406 -1405
		mu 0 3 639 642 641
		f 3 1407 1408 -1407
		mu 0 3 642 643 641
		f 3 1409 1410 -1409
		mu 0 3 643 644 641
		f 3 1411 -1411 1412
		mu 0 3 645 641 644
		f 3 -1413 1413 1414
		mu 0 3 645 644 646
		f 3 -1415 1415 1416
		mu 0 3 645 646 647
		f 3 -1416 1417 1418
		mu 0 3 647 646 648
		f 3 -1419 1419 1420
		mu 0 3 647 648 649
		f 3 -1420 1421 1422
		mu 0 3 649 648 650
		f 3 -1423 1423 1424
		mu 0 3 649 650 651
		f 3 1425 1426 -1424
		mu 0 3 650 652 651
		f 3 1427 -1427 1428
		mu 0 3 653 651 652
		f 3 1429 1430 -1429
		mu 0 3 652 654 653
		f 3 -1431 1431 1432
		mu 0 3 653 654 640
		f 3 -1432 1433 1434
		mu 0 3 640 654 655
		f 3 1435 1436 -1434
		mu 0 3 654 656 655
		f 3 1437 1438 -1437
		mu 0 3 656 657 655
		f 3 -1439 1439 1440
		mu 0 3 655 657 638
		f 3 1441 -1438 1442
		mu 0 3 652 657 656
		f 3 1443 1444 -1442
		mu 0 3 652 658 657
		f 3 1445 1446 -1445
		mu 0 3 658 659 657
		f 3 1447 1448 -1447
		mu 0 3 659 660 657
		f 3 1449 -1449 1450
		mu 0 3 634 657 660
		f 3 1451 -1448 1452
		mu 0 3 661 660 659
		f 3 1453 -1453 1454
		mu 0 3 662 661 659
		f 3 1455 -1455 1456
		mu 0 3 663 662 659
		f 3 -1457 1457 1458
		mu 0 3 663 659 664
		f 3 1459 1460 -1459
		mu 0 3 664 665 663
		f 3 1461 1462 -1461
		mu 0 3 665 666 663
		f 3 1463 1464 -1463
		mu 0 3 666 667 663
		f 3 1465 1466 -1464
		mu 0 3 666 668 667
		f 3 1467 1468 -1467
		mu 0 3 668 669 667
		f 3 1469 1470 -1469
		mu 0 3 669 670 667
		f 3 -1471 1471 1472
		mu 0 3 667 670 662
		f 3 1473 1474 -1470
		mu 0 3 669 671 670
		f 3 1475 1476 -1475
		mu 0 3 671 672 670
		f 3 -1477 1477 1478
		mu 0 3 670 672 673
		f 3 1479 -1479 1480
		mu 0 3 661 670 673
		f 3 1481 1482 -1481
		mu 0 3 673 674 661
		f 3 1483 -1482 1484
		mu 0 3 675 674 673
		f 3 1485 1486 -1484
		mu 0 3 675 676 674
		f 3 1487 1488 -1487
		mu 0 3 676 677 674
		f 3 -1489 1489 1490
		mu 0 3 674 677 678
		f 3 1491 1492 -1490
		mu 0 3 677 679 678
		f 3 1493 1494 -1493
		mu 0 3 679 633 678
		f 3 1495 1496 -1494
		mu 0 3 679 680 633
		f 3 1497 1498 -1497
		mu 0 3 680 681 633
		f 3 1499 1500 -1499
		mu 0 3 681 682 633
		f 3 -1501 1501 1502
		mu 0 3 633 682 683
		f 3 1503 1504 -1502
		mu 0 3 682 684 683
		f 3 -1505 1505 1506
		mu 0 3 683 684 632
		f 3 1507 -1506 1508
		mu 0 3 685 632 684
		f 3 1509 -1509 1510
		mu 0 3 686 685 684
		f 3 1511 -1511 1512
		mu 0 3 687 686 684
		f 3 1513 1514 -1513
		mu 0 3 684 688 687
		f 3 -1515 1515 1516
		mu 0 3 687 688 689
		f 3 1517 1518 -1517
		mu 0 3 689 690 687
		f 3 1519 1520 -1518
		mu 0 3 689 691 690
		f 3 -1521 1521 1522
		mu 0 3 690 691 692
		f 3 -1523 1523 1524
		mu 0 3 690 692 608
		f 3 1525 -1525 1526
		mu 0 3 611 690 608
		f 3 1527 -1526 1528
		mu 0 3 693 690 611
		f 3 1529 1530 -1528
		mu 0 3 693 686 690
		f 3 -1524 1531 1532
		mu 0 3 608 692 694
		f 3 -1532 1533 1534
		mu 0 3 694 692 695
		f 3 1535 1536 -1534
		mu 0 3 692 696 695
		f 3 -1537 1537 1538
		mu 0 3 695 696 697
		f 3 1539 1540 -1538
		mu 0 3 696 698 697
		f 3 -1541 1541 1542
		mu 0 3 697 698 699
		f 3 1543 -1543 1544
		mu 0 3 700 697 699
		f 3 1545 1546 -1545
		mu 0 3 699 701 700
		f 3 -1547 1547 1548
		mu 0 3 700 701 702
		f 3 1549 1550 -1548
		mu 0 3 701 703 702
		f 3 1551 1552 -1551
		mu 0 3 703 704 702
		f 3 -1553 1553 1554
		mu 0 3 702 704 705
		f 3 -1555 1555 1556
		mu 0 3 702 705 706
		f 3 -1556 1557 1558
		mu 0 3 706 705 707
		f 3 1559 -1557 1560
		mu 0 3 708 702 706
		f 3 1561 1562 -1560
		mu 0 3 708 697 702
		f 3 1563 -1562 1564
		mu 0 3 694 697 708
		f 3 -1565 1565 1566
		mu 0 3 694 708 709
		f 3 -1567 1567 1568
		mu 0 3 694 709 710
		f 3 -1568 1569 1570
		mu 0 3 710 709 607
		f 3 -1566 1571 -1570
		mu 0 3 709 708 607
		f 3 -1554 1572 -1558
		mu 0 3 705 704 707
		f 3 -1573 1573 1574
		mu 0 3 707 704 711
		f 3 -1574 1575 1576
		mu 0 3 711 704 712
		f 3 -1577 1577 1578
		mu 0 3 711 712 713
		f 3 1579 1580 -1578
		mu 0 3 712 714 713
		f 3 1581 1582 -1581
		mu 0 3 714 715 713
		f 3 1583 -1583 1584
		mu 0 3 716 713 715
		f 3 -1585 1585 1586
		mu 0 3 716 715 717
		f 3 1587 1588 -1587
		mu 0 3 717 718 716
		f 3 -1588 1589 1590
		mu 0 3 718 717 719
		f 3 1591 1592 -1590
		mu 0 3 717 720 719
		f 3 -1593 1593 1594
		mu 0 3 719 720 721
		f 3 1595 1596 -1595
		mu 0 3 721 722 719
		f 3 1597 1598 -1597
		mu 0 3 722 723 719
		f 3 -1599 1599 1600
		mu 0 3 719 723 724
		f 3 1601 1602 -1600
		mu 0 3 723 725 724
		f 3 -1603 1603 1604
		mu 0 3 724 725 726
		f 3 -1604 1605 1606
		mu 0 3 726 725 727
		f 3 1607 1608 -1607
		mu 0 3 727 728 726
		f 3 -1609 1609 1610
		mu 0 3 726 728 729
		f 3 -1610 1611 1612
		mu 0 3 729 728 730
		f 3 1613 -1613 1614
		mu 0 3 731 729 730
		f 3 -1615 1615 1616
		mu 0 3 731 730 732
		f 3 1617 1618 -1616
		mu 0 3 730 733 732
		f 3 -1619 1619 1620
		mu 0 3 732 733 734
		f 3 1621 -1620 1622
		mu 0 3 735 734 733
		f 3 -1623 1623 1624
		mu 0 3 735 733 736
		f 3 1625 1626 -1625
		mu 0 3 736 737 735
		f 3 -1627 1627 1628
		mu 0 3 735 737 738
		f 3 -1628 1629 1630
		mu 0 3 738 737 739
		f 3 1631 -1630 1632
		mu 0 3 740 739 737
		f 3 1633 -1633 1634
		mu 0 3 741 740 737
		f 3 -1634 1635 1636
		mu 0 3 740 741 742
		f 3 1637 -1636 1638
		mu 0 3 743 742 741
		f 3 1639 -1639 1640
		mu 0 3 744 743 741
		f 3 -1641 1641 1642
		mu 0 3 744 741 736
		f 3 1643 -1643 1644
		mu 0 3 745 744 736
		f 3 -1645 1645 1646
		mu 0 3 745 736 746
		f 3 1647 -1647 1648
		mu 0 3 747 745 746
		f 3 -1649 1649 1650
		mu 0 3 747 746 748
		f 3 1651 -1650 1652
		mu 0 3 749 748 746
		f 3 -1653 1653 1654
		mu 0 3 749 746 733
		f 3 1655 -1655 1656
		mu 0 3 750 749 733
		f 3 -1652 -1656 1657
		mu 0 3 748 749 750
		f 3 -1658 1658 1659
		mu 0 3 748 750 730
		f 3 1660 -1651 1661
		mu 0 3 751 747 748
		f 3 1662 -1662 1663
		mu 0 3 752 751 748
		f 3 -1664 1664 1665
		mu 0 3 752 748 728
		f 3 1666 -1663 1667
		mu 0 3 727 751 752
		f 3 1668 1669 -1667
		mu 0 3 727 753 751
		f 3 1670 1671 -1670
		mu 0 3 753 754 751
		f 3 1672 -1671 1673
		mu 0 3 755 754 753
		f 3 1674 1675 -1674
		mu 0 3 753 756 755
		f 3 1676 1677 -1676
		mu 0 3 756 757 755
		f 3 1678 1679 -1677
		mu 0 3 756 758 757
		f 3 1680 1681 -1680
		mu 0 3 758 759 757
		f 3 1682 -1682 1683
		mu 0 3 754 757 759
		f 3 1684 -1684 1685
		mu 0 3 760 754 759
		f 3 -1686 1686 1687
		mu 0 3 760 759 761
		f 3 -1688 1688 1689
		mu 0 3 760 761 762
		f 3 1690 1691 -1689
		mu 0 3 761 763 762
		f 3 -1692 1692 1693
		mu 0 3 762 763 743
		f 3 1694 1695 -1693
		mu 0 3 763 764 743
		f 3 -1696 1696 1697
		mu 0 3 743 764 765
		f 3 1698 1699 -1697
		mu 0 3 764 766 765
		f 3 1700 1701 -1700
		mu 0 3 766 767 765
		f 3 1702 -1702 1703
		mu 0 3 768 765 767
		f 3 -1704 1704 1705
		mu 0 3 768 767 769
		f 3 1706 1707 -1706
		mu 0 3 769 770 768
		f 3 1708 -1708 1709
		mu 0 3 771 768 770
		f 3 -1710 1710 1711
		mu 0 3 771 770 772
		f 3 1712 -1712 1713
		mu 0 3 773 771 772
		f 3 1714 -1714 1715
		mu 0 3 774 773 772
		f 3 1716 1717 -1716
		mu 0 3 772 767 774
		f 3 1718 -1715 1719
		mu 0 3 775 773 774
		f 3 1720 -1720 1721
		mu 0 3 766 775 774
		f 3 -1721 1722 1723
		mu 0 3 775 766 776
		f 3 1724 1725 -1724
		mu 0 3 776 763 775
		f 3 -1726 1726 1727
		mu 0 3 775 763 777
		f 3 -1727 1728 1729
		mu 0 3 777 763 778
		f 3 1730 -1729 1731
		mu 0 3 779 778 763
		f 3 1732 -1732 1733
		mu 0 3 759 779 763
		f 3 1734 -1733 1735
		mu 0 3 780 779 759
		f 3 1736 -1731 -1735
		mu 0 3 780 778 779
		f 3 -1737 1737 1738
		mu 0 3 778 780 781
		f 3 1739 -1738 1740
		mu 0 3 782 781 780
		f 3 1741 1742 -1741
		mu 0 3 780 758 782
		f 3 1743 1744 -1743
		mu 0 3 758 783 782
		f 3 -1745 1745 1746
		mu 0 3 782 783 784
		f 3 1747 1748 -1746
		mu 0 3 783 727 784
		f 3 1749 1750 -1749
		mu 0 3 727 723 784
		f 3 1751 -1747 1752
		mu 0 3 722 782 784
		f 3 -1752 1753 1754
		mu 0 3 782 722 785
		f 3 -1755 1755 1756
		mu 0 3 782 785 786
		f 3 1757 1758 -1756
		mu 0 3 785 787 786
		f 3 1759 1760 -1759
		mu 0 3 787 788 786
		f 3 1761 1762 -1761
		mu 0 3 788 789 786
		f 3 -1763 1763 1764
		mu 0 3 786 789 790
		f 3 1765 -1765 1766
		mu 0 3 777 786 790
		f 3 1767 1768 -1767
		mu 0 3 790 773 777
		f 3 -1768 1769 1770
		mu 0 3 773 790 791
		f 3 1771 1772 -1770
		mu 0 3 790 792 791
		f 3 -1773 1773 1774
		mu 0 3 791 792 793
		f 3 1775 -1774 1776
		mu 0 3 794 793 792
		f 3 1777 -1777 1778
		mu 0 3 789 794 792
		f 3 1779 1780 -1778
		mu 0 3 789 795 794
		f 3 1781 -1781 1782
		mu 0 3 796 794 795
		f 3 1783 -1783 1784
		mu 0 3 797 796 795
		f 3 1785 -1785 1786
		mu 0 3 798 797 795
		f 3 1787 -1786 1788
		mu 0 3 799 797 798
		f 3 -1789 1789 1790
		mu 0 3 799 798 800
		f 3 1791 1792 -1791
		mu 0 3 800 801 799
		f 3 -1792 1793 1794
		mu 0 3 801 800 802
		f 3 1795 -1795 1796
		mu 0 3 803 801 802
		f 3 1797 -1797 1798
		mu 0 3 804 803 802
		f 3 1799 -1799 1800
		mu 0 3 805 804 802
		f 3 1801 -1801 1802
		mu 0 3 806 805 802
		f 3 1803 -1802 1804
		mu 0 3 807 805 806
		f 3 -1805 1805 1806
		mu 0 3 807 806 808
		f 3 -1806 1807 1808
		mu 0 3 808 806 809
		f 3 1809 1810 -1809
		mu 0 3 809 810 808
		f 3 -1811 1811 1812
		mu 0 3 808 810 720
		f 3 1813 1814 -1812
		mu 0 3 810 811 720
		f 3 1815 1816 -1815
		mu 0 3 811 812 720
		f 3 1817 1818 -1817
		mu 0 3 812 813 720
		f 3 1819 1820 -1819
		mu 0 3 813 814 720
		f 3 1821 -1820 1822
		mu 0 3 815 814 813
		f 3 1823 -1823 1824
		mu 0 3 816 815 813
		f 3 1825 1826 -1824
		mu 0 3 816 798 815
		f 3 1827 -1827 1828
		mu 0 3 817 815 798
		f 3 1829 1830 -1829
		mu 0 3 798 788 817
		f 3 -1828 1831 -1822
		mu 0 3 815 817 814
		f 3 -1832 1832 1833
		mu 0 3 814 817 721
		f 3 1834 1835 -1833
		mu 0 3 817 785 721
		f 3 -1818 1836 -1825
		mu 0 3 813 812 816
		f 3 -1837 1837 1838
		mu 0 3 816 812 800
		f 3 -1838 -1816 1839
		mu 0 3 800 812 811
		f 3 1840 -1840 1841
		mu 0 3 818 800 811
		f 3 -1842 1842 1843
		mu 0 3 818 811 809
		f 3 1844 -1841 1845
		mu 0 3 806 800 818
		f 3 -1843 -1814 -1810
		mu 0 3 809 811 810
		f 3 -1846 -1844 -1808
		mu 0 3 806 818 809
		f 3 1846 1847 -1807
		mu 0 3 808 819 807
		f 3 1848 -1848 1849
		mu 0 3 820 807 819
		f 3 1850 -1850 1851
		mu 0 3 821 820 819
		f 3 -1852 1852 1853
		mu 0 3 821 819 715
		f 3 1854 1855 -1854
		mu 0 3 715 822 821
		f 3 1856 1857 -1856
		mu 0 3 822 823 821
		f 3 1858 -1857 1859
		mu 0 3 824 823 822
		f 3 -1860 1860 1861
		mu 0 3 824 822 825
		f 3 1862 -1862 1863
		mu 0 3 826 824 825
		f 3 -1864 1864 1865
		mu 0 3 826 825 704
		f 3 1866 -1866 1867
		mu 0 3 827 826 704
		f 3 1868 1869 -1867
		mu 0 3 827 828 826
		f 3 1870 1871 -1870
		mu 0 3 828 829 826
		f 3 1872 -1872 1873
		mu 0 3 830 826 829
		f 3 1874 -1874 1875
		mu 0 3 831 830 829
		f 3 1876 1877 -1875
		mu 0 3 831 832 830
		f 3 1878 -1878 1879
		mu 0 3 805 830 832
		f 3 -1879 1880 1881
		mu 0 3 830 805 833
		f 3 1882 -1882 1883
		mu 0 3 823 830 833
		f 3 -1884 1884 1885
		mu 0 3 823 833 820
		f 3 -1877 1886 1887
		mu 0 3 832 831 834
		f 3 -1888 1888 1889
		mu 0 3 832 834 804
		f 3 -1889 1890 1891
		mu 0 3 804 834 835
		f 3 -1891 1892 1893
		mu 0 3 835 834 836
		f 3 -1894 1894 1895
		mu 0 3 835 836 837
		f 3 1896 -1895 1897
		mu 0 3 838 837 836
		f 3 -1897 1898 1899
		mu 0 3 837 838 839
		f 3 1900 1901 -1899
		mu 0 3 838 840 839
		f 3 1902 -1902 1903
		mu 0 3 841 839 840
		f 3 1904 1905 -1904
		mu 0 3 840 842 841
		f 3 1906 -1906 1907
		mu 0 3 843 841 842
		f 3 1908 1909 -1908
		mu 0 3 842 844 843
		f 3 1910 -1910 1911
		mu 0 3 845 843 844
		f 3 -1912 1912 1913
		mu 0 3 845 844 846
		f 3 1914 1915 -1913
		mu 0 3 844 847 846
		f 3 -1916 1916 1917
		mu 0 3 846 847 848
		f 3 1918 1919 -1917
		mu 0 3 847 849 848
		f 3 -1920 1920 1921
		mu 0 3 848 849 850
		f 3 -1921 1922 1923
		mu 0 3 850 849 851
		f 3 -1923 1924 1925
		mu 0 3 851 849 852
		f 3 1926 -1925 1927
		mu 0 3 853 852 849
		f 3 1928 -1928 1929
		mu 0 3 854 853 849
		f 3 1930 -1929 1931
		mu 0 3 855 853 854
		f 3 1932 -1932 1933
		mu 0 3 856 855 854
		f 3 1934 -1934 1935
		mu 0 3 847 856 854
		f 3 1936 1937 -1933
		mu 0 3 856 857 855
		f 3 1938 1939 -1938
		mu 0 3 857 858 855
		f 3 -1940 1940 1941
		mu 0 3 855 858 859
		f 3 1942 1943 -1941
		mu 0 3 858 189 859
		f 3 1944 1945 -1943
		mu 0 3 858 860 189
		f 3 1946 -1945 1947
		mu 0 3 861 860 858
		f 3 1948 1949 -1947
		mu 0 3 861 862 860
		f 3 1950 1951 -1950
		mu 0 3 862 863 860
		f 3 1952 -1952 1953
		mu 0 3 864 860 863
		f 3 1954 -1954 1955
		mu 0 3 865 864 863;
	setAttr ".fc[1000:1499]"
		f 3 -1956 1956 1957
		mu 0 3 865 863 866
		f 3 -1958 1958 1959
		mu 0 3 865 866 867
		f 3 -1959 1960 1961
		mu 0 3 867 866 868
		f 3 1962 -1962 1963
		mu 0 3 869 867 868
		f 3 1964 -1964 1965
		mu 0 3 870 869 868
		f 3 -1966 1966 1967
		mu 0 3 870 868 871
		f 3 1968 -1968 1969
		mu 0 3 691 870 871
		f 3 1970 1971 -1970
		mu 0 3 871 872 691
		f 3 1972 1973 -1971
		mu 0 3 871 873 872
		f 3 -1974 1974 1975
		mu 0 3 872 873 874
		f 3 1976 1977 -1975
		mu 0 3 873 875 874
		f 3 1978 -1978 1979
		mu 0 3 876 874 875
		f 3 1980 1981 -1980
		mu 0 3 875 877 876
		f 3 -1982 1982 1983
		mu 0 3 876 877 878
		f 3 -1984 1984 1985
		mu 0 3 876 878 879
		f 3 1986 1987 -1985
		mu 0 3 878 880 879
		f 3 -1988 1988 1989
		mu 0 3 879 880 881
		f 3 -1990 1990 1991
		mu 0 3 879 881 882
		f 3 1992 -1992 1993
		mu 0 3 699 879 882
		f 3 1994 1995 -1991
		mu 0 3 881 883 882
		f 3 -1996 1996 1997
		mu 0 3 882 883 884
		f 3 -1998 1998 1999
		mu 0 3 882 884 701
		f 3 2000 2001 -1997
		mu 0 3 883 885 884
		f 3 -2002 2002 2003
		mu 0 3 884 885 886
		f 3 -2004 2004 2005
		mu 0 3 884 886 703
		f 3 2006 2007 -2005
		mu 0 3 886 827 703
		f 3 -2003 2008 2009
		mu 0 3 886 885 828
		f 3 2010 2011 -2009
		mu 0 3 885 831 828
		f 3 -2011 2012 2013
		mu 0 3 831 885 887
		f 3 2014 -2013 -2001
		mu 0 3 883 887 885
		f 3 2015 -2015 2016
		mu 0 3 888 887 883
		f 3 2017 2018 -2016
		mu 0 3 888 889 887
		f 3 2019 2020 -2019
		mu 0 3 889 834 887
		f 3 -2020 2021 2022
		mu 0 3 834 889 838
		f 3 2023 -2022 -2018
		mu 0 3 888 838 889
		f 3 -1995 2024 -2017
		mu 0 3 883 881 888
		f 3 2025 2026 -2025
		mu 0 3 881 890 888
		f 3 2027 2028 -2027
		mu 0 3 890 891 888
		f 3 -2029 2029 2030
		mu 0 3 888 891 840
		f 3 2031 2032 -2028
		mu 0 3 890 892 891
		f 3 -2033 2033 2034
		mu 0 3 891 892 856
		f 3 2035 -2035 2036
		mu 0 3 842 891 856
		f 3 2037 -2032 2038
		mu 0 3 893 892 890
		f 3 -2039 2039 2040
		mu 0 3 893 890 880
		f 3 2041 2042 -2038
		mu 0 3 893 878 892
		f 3 -2040 -2026 -1989
		mu 0 3 880 890 881
		f 3 -1987 -2042 -2041
		mu 0 3 880 878 893
		f 3 2043 -1986 2044
		mu 0 3 698 876 879
		f 3 2045 -2043 -1983
		mu 0 3 877 892 878
		f 3 2046 2047 -2046
		mu 0 3 877 894 892
		f 3 2048 2049 -2048
		mu 0 3 894 861 892
		f 3 -2050 2050 2051
		mu 0 3 892 861 857
		f 3 2052 -2047 2053
		mu 0 3 862 894 877
		f 3 -2054 -1981 2054
		mu 0 3 862 877 875
		f 3 -1979 -2044 2055
		mu 0 3 874 876 698
		f 3 2056 2057 -1977
		mu 0 3 873 866 875
		f 3 2058 2059 -1976
		mu 0 3 874 696 872
		f 3 -1969 2060 2061
		mu 0 3 870 691 895
		f 3 2062 2063 -2062
		mu 0 3 895 896 870
		f 3 2064 2065 -2064
		mu 0 3 896 897 870
		f 3 2066 2067 -2065
		mu 0 3 896 898 897
		f 3 2068 -2068 2069
		mu 0 3 899 897 898
		f 3 -2070 2070 2071
		mu 0 3 899 898 900
		f 3 2072 -2072 2073
		mu 0 3 901 899 900
		f 3 -2074 2074 2075
		mu 0 3 901 900 902
		f 3 -2076 2076 2077
		mu 0 3 901 902 192
		f 3 -2078 2078 2079
		mu 0 3 901 192 867
		f 3 2080 2081 -2079
		mu 0 3 192 864 867
		f 3 2082 2083 -2075
		mu 0 3 900 903 902
		f 3 -2084 2084 2085
		mu 0 3 902 903 904
		f 3 2086 2087 -2085
		mu 0 3 903 905 904
		f 3 -2088 2088 2089
		mu 0 3 904 905 906
		f 3 -2090 2090 2091
		mu 0 3 904 906 907
		f 3 -2092 2092 2093
		mu 0 3 904 907 193
		f 3 2094 2095 -2091
		mu 0 3 906 234 907
		f 3 2096 -2096 2097
		mu 0 3 194 907 234
		f 3 2098 2099 -2089
		mu 0 3 905 908 906
		f 3 -2100 2100 2101
		mu 0 3 906 908 909
		f 3 -2102 2102 2103
		mu 0 3 906 909 235
		f 3 -2101 2104 2105
		mu 0 3 909 908 910
		f 3 2106 2107 -2105
		mu 0 3 908 911 910
		f 3 -2108 2108 2109
		mu 0 3 910 911 912
		f 3 2110 -2109 2111
		mu 0 3 913 912 911
		f 3 2112 -2112 2113
		mu 0 3 914 913 911
		f 3 -2114 2114 2115
		mu 0 3 914 911 915
		f 3 2116 -2116 2117
		mu 0 3 916 914 915
		f 3 -2118 2118 2119
		mu 0 3 916 915 917
		f 3 -2119 2120 2121
		mu 0 3 917 915 918
		f 3 2122 2123 -2122
		mu 0 3 918 919 917
		f 3 -2124 2124 2125
		mu 0 3 917 919 920
		f 3 2126 -2126 2127
		mu 0 3 921 917 920
		f 3 -2128 2128 2129
		mu 0 3 921 920 922
		f 3 2130 2131 -2130
		mu 0 3 922 923 921
		f 3 2132 2133 -2132
		mu 0 3 923 924 921
		f 3 2134 2135 -2134
		mu 0 3 924 925 921
		f 3 -2136 2136 2137
		mu 0 3 921 925 916
		f 3 -2135 2138 2139
		mu 0 3 925 924 926
		f 3 2140 -2139 2141
		mu 0 3 927 926 924
		f 3 2142 -2141 2143
		mu 0 3 928 926 927
		f 3 2144 -2144 2145
		mu 0 3 929 928 927
		f 3 -2146 2146 2147
		mu 0 3 929 927 930
		f 3 -2147 2148 2149
		mu 0 3 930 927 931
		f 3 2150 2151 -2149
		mu 0 3 927 923 931
		f 3 2152 2153 -2152
		mu 0 3 923 932 931
		f 3 -2154 2154 2155
		mu 0 3 931 932 933
		f 3 -2156 2156 2157
		mu 0 3 931 933 671
		f 3 2158 -2158 2159
		mu 0 3 934 931 671
		f 3 -2159 2160 2161
		mu 0 3 931 934 935
		f 3 2162 2163 -2161
		mu 0 3 934 936 935
		f 3 2164 -2164 2165
		mu 0 3 937 935 936
		f 3 2166 -2166 2167
		mu 0 3 938 937 936
		f 3 -2168 2168 2169
		mu 0 3 938 936 668
		f 3 -2169 2170 2171
		mu 0 3 668 936 939
		f 3 2172 -2170 2173
		mu 0 3 665 938 668
		f 3 2174 -2173 2175
		mu 0 3 940 938 665
		f 3 2176 -2175 2177
		mu 0 3 941 938 940
		f 3 2178 -2178 2179
		mu 0 3 942 941 940
		f 3 -2180 2180 2181
		mu 0 3 942 940 943
		f 3 -2181 2182 2183
		mu 0 3 943 940 944
		f 3 -2184 2184 2185
		mu 0 3 943 944 945
		f 3 2186 2187 -2186
		mu 0 3 945 946 943
		f 3 -2188 2188 2189
		mu 0 3 943 946 947
		f 3 2190 -2189 2191
		mu 0 3 948 947 946
		f 3 2192 -2192 2193
		mu 0 3 949 948 946
		f 3 2194 -2193 2195
		mu 0 3 950 948 949
		f 3 2196 -2196 2197
		mu 0 3 951 950 949
		f 3 2198 -2198 2199
		mu 0 3 952 951 949
		f 3 2200 -2200 2201
		mu 0 3 953 952 949
		f 3 -2202 2202 2203
		mu 0 3 953 949 945
		f 3 -2204 2204 2205
		mu 0 3 953 945 954
		f 3 2206 -2206 2207
		mu 0 3 955 953 954
		f 3 2208 2209 -2208
		mu 0 3 954 956 955
		f 3 -2210 2210 2211
		mu 0 3 955 956 957
		f 3 2212 2213 -2212
		mu 0 3 957 958 955
		f 3 2214 -2214 2215
		mu 0 3 959 955 958
		f 3 -2216 2216 2217
		mu 0 3 959 958 960
		f 3 -2217 2218 2219
		mu 0 3 960 958 961
		f 3 2220 -2220 2221
		mu 0 3 962 960 961
		f 3 2222 -2222 2223
		mu 0 3 963 962 961
		f 3 2224 2225 -2224
		mu 0 3 961 964 963
		f 3 2226 -2226 2227
		mu 0 3 965 963 964
		f 3 2228 2229 -2228
		mu 0 3 964 966 965
		f 3 2230 2231 -2230
		mu 0 3 966 967 965
		f 3 2232 -2232 2233
		mu 0 3 968 965 967
		f 3 2234 2235 -2234
		mu 0 3 967 969 968
		f 3 2236 2237 -2236
		mu 0 3 969 970 968
		f 3 2238 -2238 2239
		mu 0 3 971 968 970
		f 3 2240 -2240 2241
		mu 0 3 972 971 970
		f 3 2242 -2242 2243
		mu 0 3 973 972 970
		f 3 2244 -2244 2245
		mu 0 3 974 973 970
		f 3 -2246 2246 2247
		mu 0 3 974 970 975
		f 3 2248 -2248 2249
		mu 0 3 976 974 975
		f 3 -2250 2250 2251
		mu 0 3 976 975 977
		f 3 2252 -2252 2253
		mu 0 3 978 976 977
		f 3 2254 -2254 2255
		mu 0 3 979 978 977
		f 3 -2255 2256 2257
		mu 0 3 978 979 980
		f 3 -2258 2258 2259
		mu 0 3 978 980 981
		f 3 2260 2261 -2259
		mu 0 3 980 982 981
		f 3 -2262 2262 2263
		mu 0 3 981 982 983
		f 3 -2263 2264 2265
		mu 0 3 983 982 984
		f 3 -2265 2266 2267
		mu 0 3 984 982 355
		f 3 2268 -2266 2269
		mu 0 3 985 983 984
		f 3 -2270 2270 2271
		mu 0 3 985 984 354
		f 3 -2269 2272 2273
		mu 0 3 983 985 986
		f 3 2274 -2274 2275
		mu 0 3 987 983 986
		f 3 -2276 2276 2277
		mu 0 3 987 986 988
		f 3 2278 -2278 2279
		mu 0 3 989 987 988
		f 3 2280 -2280 2281
		mu 0 3 990 989 988
		f 3 2282 2283 -2282
		mu 0 3 988 991 990
		f 3 2284 2285 -2284
		mu 0 3 991 992 990
		f 3 2286 -2286 2287
		mu 0 3 993 990 992
		f 3 2288 2289 -2288
		mu 0 3 992 994 993
		f 3 2290 2291 -2290
		mu 0 3 994 995 993
		f 3 2292 2293 -2292
		mu 0 3 995 996 993
		f 3 2294 2295 -2293
		mu 0 3 995 997 996
		f 3 -2296 2296 2297
		mu 0 3 996 997 998
		f 3 2298 2299 -2297
		mu 0 3 997 989 998
		f 3 2300 2301 -2299
		mu 0 3 997 981 989
		f 3 -2298 2302 2303
		mu 0 3 996 998 990
		f 3 2304 2305 -2295
		mu 0 3 995 999 997
		f 3 2306 2307 -2306
		mu 0 3 999 1000 997
		f 3 2308 2309 -2308
		mu 0 3 1000 1001 997
		f 3 2310 -2310 2311
		mu 0 3 976 997 1001
		f 3 -2309 2312 2313
		mu 0 3 1001 1000 974
		f 3 2314 2315 -2313
		mu 0 3 1000 1002 974
		f 3 -2315 2316 2317
		mu 0 3 1002 1000 1003
		f 3 2318 -2318 2319
		mu 0 3 1004 1002 1003
		f 3 2320 -2320 2321
		mu 0 3 1005 1004 1003
		f 3 2322 2323 -2322
		mu 0 3 1003 1006 1005
		f 3 2324 2325 -2324
		mu 0 3 1006 1007 1005
		f 3 -2326 2326 2327
		mu 0 3 1005 1007 999
		f 3 2328 2329 -2327
		mu 0 3 1007 1008 999
		f 3 2330 2331 -2329
		mu 0 3 1007 1009 1008
		f 3 2332 -2332 2333
		mu 0 3 1010 1008 1009
		f 3 2334 -2334 2335
		mu 0 3 1006 1010 1009
		f 3 2336 2337 -2333
		mu 0 3 1010 1000 1008
		f 3 2338 -2328 2339
		mu 0 3 1011 1005 999
		f 3 2340 -2340 2341
		mu 0 3 1012 1011 999
		f 3 -2342 2342 2343
		mu 0 3 1012 999 992
		f 3 2344 -2344 2345
		mu 0 3 1013 1012 992
		f 3 2346 2347 -2346
		mu 0 3 992 1014 1013
		f 3 2348 -2348 2349
		mu 0 3 1015 1013 1014
		f 3 2350 2351 -2350
		mu 0 3 1014 327 1015
		f 3 2352 2353 -2351
		mu 0 3 1014 1016 327
		f 3 2354 2355 -2354
		mu 0 3 1016 1017 327
		f 3 2356 -2355 2357
		mu 0 3 333 1017 1016
		f 3 -2358 2358 2359
		mu 0 3 333 1016 1018
		f 3 2360 -2360 2361
		mu 0 3 1019 333 1018
		f 3 2362 2363 -2362
		mu 0 3 1018 1020 1019
		f 3 2364 -2364 2365
		mu 0 3 337 1019 1020
		f 3 -2363 2366 2367
		mu 0 3 1020 1018 1021
		f 3 2368 -2368 2369
		mu 0 3 339 1020 1021
		f 3 -2370 2370 2371
		mu 0 3 339 1021 1022
		f 3 2372 2373 -2371
		mu 0 3 1021 1023 1022
		f 3 -2374 2374 2375
		mu 0 3 1022 1023 1024
		f 3 2376 2377 -2376
		mu 0 3 1024 1025 1022
		f 3 2378 -2377 2379
		mu 0 3 991 1025 1024
		f 3 -2379 2380 2381
		mu 0 3 1025 991 340
		f 3 2382 2383 -2381
		mu 0 3 991 1026 340
		f 3 -2384 2384 2385
		mu 0 3 340 1026 1027
		f 3 2386 -2386 2387
		mu 0 3 1028 340 1027
		f 3 2388 2389 -2388
		mu 0 3 1027 986 1028
		f 3 -2390 2390 2391
		mu 0 3 1028 986 350
		f 3 2392 -2389 2393
		mu 0 3 1029 986 1027
		f 3 -2394 -2385 2394
		mu 0 3 1029 1027 1026
		f 3 2395 -2395 -2383
		mu 0 3 991 1029 1026
		f 3 -2375 2396 -2380
		mu 0 3 1024 1023 991
		f 3 -2373 2397 2398
		mu 0 3 1023 1021 1014
		f 3 -2372 -2378 2399
		mu 0 3 339 1022 1025
		f 3 -2398 -2367 2400
		mu 0 3 1014 1021 1018
		f 3 -2361 -2365 2401
		mu 0 3 333 1019 337
		f 3 -2353 -2401 -2359
		mu 0 3 1016 1014 1018
		f 3 2402 2403 -2349
		mu 0 3 1015 323 1013
		f 3 2404 -2404 2405
		mu 0 3 1030 1013 323
		f 3 2406 -2406 2407
		mu 0 3 1031 1030 323
		f 3 -2407 2408 2409
		mu 0 3 1030 1031 1032
		f 3 -2410 2410 2411
		mu 0 3 1030 1032 1033
		f 3 2412 2413 -2411
		mu 0 3 1032 1034 1033
		f 3 2414 -2414 2415
		mu 0 3 1035 1033 1034
		f 3 2416 -2416 2417
		mu 0 3 1036 1035 1034
		f 3 -2418 2418 2419
		mu 0 3 1036 1034 1037
		f 3 2420 -2419 2421
		mu 0 3 1031 1037 1034
		f 3 2422 -2421 2423
		mu 0 3 322 1037 1031
		f 3 2424 2425 -2423
		mu 0 3 322 1038 1037
		f 3 2426 -2426 2427
		mu 0 3 1039 1037 1038
		f 3 -2428 2428 2429
		mu 0 3 1039 1038 1040
		f 3 -2429 2430 2431
		mu 0 3 1040 1038 1041
		f 3 2432 -2432 2433
		mu 0 3 313 1040 1041
		f 3 2434 -2430 2435
		mu 0 3 283 1039 1040
		f 3 -2436 2436 2437
		mu 0 3 283 1040 312
		f 3 2438 -2427 -2435
		mu 0 3 283 1037 1039
		f 3 -2431 -2425 2439
		mu 0 3 1041 1038 322
		f 3 -2440 2440 2441
		mu 0 3 1041 322 1042
		f 3 2442 -2442 2443
		mu 0 3 315 1041 1042
		f 3 2444 -2420 2445
		mu 0 3 281 1036 1037
		f 3 2446 2447 -2445
		mu 0 3 281 1043 1036
		f 3 2448 -2417 -2448
		mu 0 3 1043 1035 1036
		f 3 2449 2450 -2449
		mu 0 3 1043 1044 1035
		f 3 2451 -2451 2452
		mu 0 3 1045 1035 1044
		f 3 2453 -2453 2454
		mu 0 3 1046 1045 1044
		f 3 2455 2456 -2455
		mu 0 3 1044 1047 1046
		f 3 2457 2458 -2457
		mu 0 3 1047 1048 1046
		f 3 -2459 2459 2460
		mu 0 3 1046 1048 1049
		f 3 -2461 2461 2462
		mu 0 3 1046 1049 1050
		f 3 2463 -2463 2464
		mu 0 3 1051 1046 1050
		f 3 -2465 2465 2466
		mu 0 3 1051 1050 1052
		f 3 2467 -2467 2468
		mu 0 3 1053 1051 1052
		f 3 2469 2470 -2469
		mu 0 3 1052 1005 1053
		f 3 2471 2472 -2470
		mu 0 3 1052 1054 1005
		f 3 -2473 2473 2474
		mu 0 3 1005 1054 973
		f 3 2475 2476 -2474
		mu 0 3 1054 1055 973
		f 3 2477 2478 -2476
		mu 0 3 1054 1056 1055
		f 3 -2479 2479 2480
		mu 0 3 1055 1056 972
		f 3 2481 2482 -2478
		mu 0 3 1054 1057 1056
		f 3 -2483 2483 2484
		mu 0 3 1056 1057 1058
		f 3 2485 2486 -2485
		mu 0 3 1058 971 1056
		f 3 -2486 2487 2488
		mu 0 3 971 1058 963
		f 3 2489 2490 -2484
		mu 0 3 1057 1059 1058
		f 3 2491 2492 -2491
		mu 0 3 1059 1060 1058
		f 3 -2493 2493 2494
		mu 0 3 1058 1060 962
		f 3 2495 2496 -2492
		mu 0 3 1059 951 1060
		f 3 -2497 2497 2498
		mu 0 3 1060 951 960
		f 3 2499 -2496 2500
		mu 0 3 1061 951 1059
		f 3 2501 -2501 2502
		mu 0 3 1062 1061 1059
		f 3 2503 -2502 2504
		mu 0 3 1063 1061 1062
		f 3 2505 -2505 2506
		mu 0 3 1048 1063 1062
		f 3 2507 -2506 2508
		mu 0 3 1064 1063 1048
		f 3 2509 -2509 2510
		mu 0 3 1065 1064 1048
		f 3 -2511 2511 2512
		mu 0 3 1065 1048 1066
		f 3 -2513 2513 2514
		mu 0 3 1065 1066 1067
		f 3 2515 2516 -2515
		mu 0 3 1067 1068 1065
		f 3 2517 2518 -2517
		mu 0 3 1068 1069 1065
		f 3 2519 2520 -2519
		mu 0 3 1069 1070 1065
		f 3 2521 2522 -2520
		mu 0 3 1069 1071 1070
		f 3 -2523 2523 2524
		mu 0 3 1070 1071 1072
		f 3 2525 2526 -2525
		mu 0 3 1072 1064 1070
		f 3 2527 2528 -2524
		mu 0 3 1071 1073 1072
		f 3 -2529 2529 2530
		mu 0 3 1072 1073 1063
		f 3 2531 2532 -2528
		mu 0 3 1071 1074 1073
		f 3 2533 -2533 2534
		mu 0 3 1061 1073 1074
		f 3 2535 2536 -2535
		mu 0 3 1074 947 1061
		f 3 2537 2538 -2537
		mu 0 3 947 950 1061
		f 3 2539 -2536 2540
		mu 0 3 942 947 1074
		f 3 2541 2542 -2532
		mu 0 3 1071 1075 1074
		f 3 2543 2544 -2543
		mu 0 3 1075 1076 1074
		f 3 -2545 2545 2546
		mu 0 3 1074 1076 941
		f 3 2547 -2546 2548
		mu 0 3 935 941 1076
		f 3 2549 -2544 2550
		mu 0 3 1077 1076 1075
		f 3 -2551 2551 2552
		mu 0 3 1077 1075 1078
		f 3 2553 2554 -2553
		mu 0 3 1078 249 1077
		f 3 2555 2556 -2550
		mu 0 3 1077 930 1076
		f 3 2557 -2552 -2542
		mu 0 3 1071 1078 1075
		f 3 2558 -2558 -2522
		mu 0 3 1069 1078 1071
		f 3 2559 -2559 -2518
		mu 0 3 1068 1078 1069
		f 3 2560 -2560 2561
		mu 0 3 253 1078 1068
		f 3 -2516 2562 -2562
		mu 0 3 1068 1067 253
		f 3 2563 -2563 2564
		mu 0 3 279 253 1067
		f 3 -2564 2565 2566
		mu 0 3 253 279 1079
		f 3 -2565 -2514 2567
		mu 0 3 279 1067 1066
		f 3 -2568 2568 2569
		mu 0 3 279 1066 1080
		f 3 -2569 2570 2571
		mu 0 3 1080 1066 1047
		f 3 -2510 -2521 -2527
		mu 0 3 1064 1065 1070
		f 3 -2531 -2508 -2526
		mu 0 3 1072 1063 1064
		f 3 -2534 -2504 -2530
		mu 0 3 1073 1061 1063
		f 3 -2503 -2490 2572
		mu 0 3 1062 1059 1057
		f 3 2573 -2573 2574
		mu 0 3 1049 1062 1057
		f 3 2575 -2575 -2482
		mu 0 3 1054 1049 1057
		f 3 2576 -2576 -2472
		mu 0 3 1052 1049 1054
		f 3 2577 -2468 2578
		mu 0 3 1081 1051 1053
		f 3 -2579 2579 2580
		mu 0 3 1081 1053 1012
		f 3 2581 2582 -2578
		mu 0 3 1081 1082 1051
		f 3 2583 2584 -2583
		mu 0 3 1082 1083 1051
		f 3 2585 2586 -2584
		mu 0 3 1082 1033 1083
		f 3 2587 2588 -2582
		mu 0 3 1081 1084 1082
		f 3 2589 2590 -2589
		mu 0 3 1084 1030 1082
		f 3 2591 -2588 2592
		mu 0 3 1013 1084 1081
		f 3 2593 -2464 -2585
		mu 0 3 1083 1046 1051
		f 3 -2577 -2466 -2462
		mu 0 3 1049 1052 1050
		f 3 -2574 -2460 -2507
		mu 0 3 1062 1049 1048
		f 3 -2512 -2458 -2571
		mu 0 3 1066 1048 1047
		f 3 -2456 2594 -2572
		mu 0 3 1047 1044 1080
		f 3 2595 -2454 -2594
		mu 0 3 1083 1045 1046
		f 3 -2452 -2596 2596
		mu 0 3 1035 1045 1083
		f 3 -2595 -2450 2597
		mu 0 3 1080 1044 1043
		f 3 2598 -2598 2599
		mu 0 3 280 1080 1043
		f 3 -2415 -2597 -2587
		mu 0 3 1033 1035 1083
		f 3 -2586 -2591 -2412
		mu 0 3 1033 1082 1030
		f 3 -2422 -2413 -2409
		mu 0 3 1031 1034 1032
		f 3 -2590 -2592 -2405
		mu 0 3 1030 1084 1013
		f 3 -2399 -2347 2600
		mu 0 3 1023 1014 992
		f 3 -2593 -2581 -2345
		mu 0 3 1013 1081 1012
		f 3 2601 -2341 -2580
		mu 0 3 1053 1011 1012
		f 3 -2471 -2339 -2602
		mu 0 3 1053 1005 1011
		f 3 -2336 -2331 -2325
		mu 0 3 1006 1009 1007
		f 3 2602 -2335 -2323
		mu 0 3 1003 1010 1006
		f 3 -2321 -2475 2603
		mu 0 3 1004 1005 973
		f 3 -2604 2604 -2319
		mu 0 3 1004 973 1002
		f 3 -2317 -2337 -2603
		mu 0 3 1003 1000 1010
		f 3 -2338 -2307 -2330
		mu 0 3 1008 1000 999
		f 3 -2305 -2291 2605
		mu 0 3 999 995 994
		f 3 -2343 -2606 -2289
		mu 0 3 992 999 994
		f 3 -2304 -2287 -2294
		mu 0 3 996 990 993
		f 3 -2601 -2285 -2397
		mu 0 3 1023 992 991
		f 3 -2396 -2283 2606
		mu 0 3 1029 991 988
		f 3 -2300 -2281 -2303
		mu 0 3 998 989 990
		f 3 -2302 2607 -2279
		mu 0 3 989 981 987
		f 3 -2277 -2393 -2607
		mu 0 3 988 986 1029
		f 3 -2391 -2273 2608
		mu 0 3 350 986 985
		f 3 -2608 -2264 -2275
		mu 0 3 987 981 983
		f 3 -2261 2609 2610
		mu 0 3 982 980 1085
		f 3 -2610 2611 2612
		mu 0 3 1085 980 1086
		f 3 2613 -2613 2614
		mu 0 3 1087 1085 1086
		f 3 -2615 2615 2616
		mu 0 3 1087 1086 979
		f 3 2617 -2617 2618
		mu 0 3 1088 1087 979
		f 3 2619 -2619 2620
		mu 0 3 975 1088 979
		f 3 2621 -2620 2622
		mu 0 3 1089 1088 975
		f 3 -2623 2623 2624
		mu 0 3 1089 975 1090
		f 3 -2625 2625 2626
		mu 0 3 1089 1090 1091
		f 3 -2627 2627 2628
		mu 0 3 1089 1091 1092
		f 3 2629 -2629 2630
		mu 0 3 1093 1089 1092
		f 3 -2631 2631 2632
		mu 0 3 1093 1092 1094
		f 3 -2632 2633 2634
		mu 0 3 1094 1092 1095
		f 3 2635 -2635 2636
		mu 0 3 1096 1094 1095
		f 3 2637 2638 -2637
		mu 0 3 1095 1097 1096
		f 3 2639 -2639 2640
		mu 0 3 1098 1096 1097
		f 3 -2641 2641 2642
		mu 0 3 1098 1097 1099
		f 3 2643 -2642 2644
		mu 0 3 1100 1099 1097
		f 3 2645 2646 -2644
		mu 0 3 1100 1101 1099
		f 3 2647 2648 -2647
		mu 0 3 1101 1102 1099
		f 3 2649 2650 -2649
		mu 0 3 1102 1103 1099
		f 3 2651 -2651 2652
		mu 0 3 1104 1099 1103
		f 3 -2653 2653 2654
		mu 0 3 1104 1103 1105
		f 3 2655 2656 -2655
		mu 0 3 1105 1106 1104
		f 3 2657 -2657 2658
		mu 0 3 1107 1104 1106
		f 3 -2659 2659 2660
		mu 0 3 1107 1106 1108
		f 3 2661 -2660 2662
		mu 0 3 658 1108 1106
		f 3 2663 -2661 2664
		mu 0 3 650 1107 1108
		f 3 2665 -2664 2666
		mu 0 3 1109 1107 650
		f 3 2667 2668 -2666
		mu 0 3 1109 1098 1107
		f 3 2669 -2658 -2669
		mu 0 3 1098 1104 1107
		f 3 -2656 2670 2671
		mu 0 3 1106 1105 659
		f 3 -2671 2672 2673
		mu 0 3 659 1105 1110
		f 3 -2673 2674 2675
		mu 0 3 1110 1105 1111
		f 3 -2675 2676 2677
		mu 0 3 1111 1105 1112
		f 3 2678 -2678 2679
		mu 0 3 957 1111 1112
		f 3 -2680 2680 2681
		mu 0 3 957 1112 1113
		f 3 -2681 2682 2683
		mu 0 3 1113 1112 1114
		f 3 2684 -2683 2685
		mu 0 3 1115 1114 1112
		f 3 2686 -2685 2687
		mu 0 3 1102 1114 1115
		f 3 2688 -2687 2689
		mu 0 3 966 1114 1102
		f 3 -2684 2690 2691
		mu 0 3 1113 1114 964
		f 3 -2686 -2677 2692
		mu 0 3 1115 1112 1105
		f 3 2693 -2676 -2679
		mu 0 3 957 1110 1111
		f 3 2694 2695 -2694
		mu 0 3 957 1116 1110
		f 3 -2696 2696 2697
		mu 0 3 1110 1116 664
		f 3 2698 2699 -2697
		mu 0 3 1116 940 664
		f 3 -2699 2700 2701
		mu 0 3 940 1116 956
		f 3 2702 -2693 -2654
		mu 0 3 1103 1115 1105
		f 3 -2703 -2650 -2688
		mu 0 3 1115 1103 1102
		f 3 -2648 2703 -2690
		mu 0 3 1102 1101 966
		f 3 2704 -2704 2705
		mu 0 3 1117 966 1101
		f 3 2706 -2706 -2646
		mu 0 3 1100 1117 1101
		f 3 2707 2708 -2707
		mu 0 3 1100 1095 1117
		f 3 2709 -2709 2710
		mu 0 3 967 1117 1095
		f 3 2711 2712 -2711
		mu 0 3 1095 1091 967
		f 3 -2652 -2670 -2643
		mu 0 3 1099 1104 1098
		f 3 -2640 -2668 2713
		mu 0 3 1096 1098 1109
		f 3 2714 2715 -2714
		mu 0 3 1109 1118 1096
		f 3 2716 -2715 2717
		mu 0 3 648 1118 1109
		f 3 -2708 -2645 -2638
		mu 0 3 1095 1100 1097
		f 3 2718 -2636 -2716
		mu 0 3 1118 1094 1096
		f 3 2719 -2719 2720
		mu 0 3 1119 1094 1118
		f 3 2721 -2721 2722
		mu 0 3 1120 1119 1118
		f 3 2723 -2723 2724
		mu 0 3 1121 1120 1118
		f 3 -2725 2725 2726
		mu 0 3 1121 1118 646
		f 3 2727 -2724 2728
		mu 0 3 1122 1120 1121
		f 3 2729 -2729 2730
		mu 0 3 1123 1122 1121
		f 3 2731 -2731 2732
		mu 0 3 1124 1123 1121
		f 3 2733 2734 -2733
		mu 0 3 1121 644 1124
		f 3 2735 -2735 2736
		mu 0 3 1125 1124 644
		f 3 2737 -2736 2738
		mu 0 3 1126 1124 1125
		f 3 -2739 2739 2740
		mu 0 3 1126 1125 1127
		f 3 -2740 2741 2742
		mu 0 3 1127 1125 1128
		f 3 2743 2744 -2743
		mu 0 3 1128 1129 1127
		f 3 2745 -2745 2746
		mu 0 3 1130 1127 1129
		f 3 -2747 2747 2748
		mu 0 3 1130 1129 1131
		f 3 2749 2750 -2748
		mu 0 3 1129 1132 1131
		f 3 2751 -2751 2752
		mu 0 3 1133 1131 1132
		f 3 2753 -2753 2754
		mu 0 3 1128 1133 1132
		f 3 2755 2756 -2754
		mu 0 3 1128 1134 1133
		f 3 2757 2758 -2757
		mu 0 3 1134 1135 1133
		f 3 2759 2760 -2759
		mu 0 3 1135 1136 1133
		f 3 2761 -2761 2762
		mu 0 3 1137 1133 1136
		f 3 2763 2764 -2763
		mu 0 3 1136 1138 1137
		f 3 2765 -2765 2766
		mu 0 3 1139 1137 1138
		f 3 -2767 2767 2768
		mu 0 3 1139 1138 1140
		f 3 2769 -2768 2770
		mu 0 3 1141 1140 1138
		f 3 -2771 2771 2772
		mu 0 3 1141 1138 1142
		f 3 2773 2774 -2772
		mu 0 3 1138 1143 1142
		f 3 -2775 2775 2776
		mu 0 3 1142 1143 1144
		f 3 -2776 2777 2778
		mu 0 3 1144 1143 1145
		f 3 2779 2780 -2779
		mu 0 3 1145 1146 1144
		f 3 2781 -2781 2782
		mu 0 3 1147 1144 1146
		f 3 -2783 2783 2784
		mu 0 3 1147 1146 1148
		f 3 2785 2786 -2784
		mu 0 3 1146 1149 1148
		f 3 2787 2788 -2787
		mu 0 3 1149 1150 1148
		f 3 2789 -2789 2790
		mu 0 3 1151 1148 1150
		f 3 2791 -2791 2792
		mu 0 3 625 1151 1150
		f 3 2793 -2793 2794
		mu 0 3 1152 625 1150
		f 3 2795 -2792 2796
		mu 0 3 1153 1151 625
		f 3 2797 -2796 2798
		mu 0 3 1154 1151 1153
		f 3 2799 2800 -2799
		mu 0 3 1153 616 1154
		f 3 -2790 -2798 2801
		mu 0 3 1148 1151 1154
		f 3 2802 2803 -2802
		mu 0 3 1154 1155 1148
		f 3 2804 2805 -2804
		mu 0 3 1155 1156 1148
		f 3 -2806 2806 2807
		mu 0 3 1148 1156 1157
		f 3 2808 -2807 2809
		mu 0 3 1158 1157 1156
		f 3 2810 2811 -2810
		mu 0 3 1156 1159 1158
		f 3 2812 -2812 2813
		mu 0 3 1160 1158 1159
		f 3 -2814 2814 2815
		mu 0 3 1160 1159 1161
		f 3 -2816 2816 2817
		mu 0 3 1160 1161 1162
		f 3 2818 2819 -2817
		mu 0 3 1161 593 1162
		f 3 -2820 2820 2821
		mu 0 3 1162 593 1163
		f 3 2822 2823 -2821
		mu 0 3 593 589 1163
		f 3 -2824 2824 2825
		mu 0 3 1163 589 1164
		f 3 2826 -2826 2827
		mu 0 3 1165 1163 1164
		f 3 2828 -2828 2829
		mu 0 3 1166 1165 1164
		f 3 2830 -2830 2831
		mu 0 3 1167 1166 1164
		f 3 2832 2833 -2832
		mu 0 3 1164 1168 1167
		f 3 -2834 2834 2835
		mu 0 3 1167 1168 583
		f 3 -2833 2836 2837
		mu 0 3 1168 1164 1169
		f 3 -2838 2838 2839
		mu 0 3 1168 1169 586
		f 3 -2831 2840 2841
		mu 0 3 1166 1167 1170
		f 3 -2841 2842 2843
		mu 0 3 1170 1167 581
		f 3 2844 2845 -2842
		mu 0 3 1170 1171 1166
		f 3 -2846 2846 2847
		mu 0 3 1166 1171 1172
		f 3 2848 2849 -2847
		mu 0 3 1171 1173 1172
		f 3 2850 2851 -2850
		mu 0 3 1173 1174 1172
		f 3 2852 2853 -2852
		mu 0 3 1174 1162 1172
		f 3 2854 -2854 2855
		mu 0 3 1165 1172 1162;
	setAttr ".fc[1500:1999]"
		f 3 2856 -2853 2857
		mu 0 3 1175 1162 1174
		f 3 -2858 2858 2859
		mu 0 3 1175 1174 1176
		f 3 2860 2861 -2860
		mu 0 3 1176 1177 1175
		f 3 -2862 2862 2863
		mu 0 3 1175 1177 1178
		f 3 2864 2865 -2864
		mu 0 3 1178 1179 1175
		f 3 -2865 2866 2867
		mu 0 3 1179 1178 1180
		f 3 2868 2869 -2867
		mu 0 3 1178 1181 1180
		f 3 -2870 2870 2871
		mu 0 3 1180 1181 1158
		f 3 2872 2873 -2871
		mu 0 3 1181 1182 1158
		f 3 -2873 2874 2875
		mu 0 3 1182 1181 1183
		f 3 2876 2877 -2876
		mu 0 3 1183 1157 1182
		f 3 -2877 2878 2879
		mu 0 3 1157 1183 1147
		f 3 -2879 2880 2881
		mu 0 3 1147 1183 1184
		f 3 2882 -2881 2883
		mu 0 3 1185 1184 1183
		f 3 2884 -2884 2885
		mu 0 3 1186 1185 1183
		f 3 -2885 2886 2887
		mu 0 3 1185 1186 1187
		f 3 -2887 2888 2889
		mu 0 3 1187 1186 1188
		f 3 2890 -2889 2891
		mu 0 3 1189 1188 1186
		f 3 2892 2893 -2892
		mu 0 3 1186 1181 1189
		f 3 2894 -2894 2895
		mu 0 3 1190 1189 1181
		f 3 -2895 2896 2897
		mu 0 3 1189 1190 1191
		f 3 2898 -2897 2899
		mu 0 3 1192 1191 1190
		f 3 2900 -2900 2901
		mu 0 3 1193 1192 1190
		f 3 2902 2903 -2902
		mu 0 3 1190 1178 1193
		f 3 -2901 2904 2905
		mu 0 3 1192 1193 1194
		f 3 2906 -2906 2907
		mu 0 3 1195 1192 1194
		f 3 -2908 2908 2909
		mu 0 3 1195 1194 1196
		f 3 2910 -2910 2911
		mu 0 3 1197 1195 1196
		f 3 -2912 2912 2913
		mu 0 3 1197 1196 1198
		f 3 -2913 2914 2915
		mu 0 3 1198 1196 1199
		f 3 -2916 2916 2917
		mu 0 3 1198 1199 1200
		f 3 2918 -2918 2919
		mu 0 3 1201 1198 1200
		f 3 -2920 2920 2921
		mu 0 3 1201 1200 1202
		f 3 -2922 2922 2923
		mu 0 3 1201 1202 1203
		f 3 2924 -2924 2925
		mu 0 3 1204 1201 1203
		f 3 2926 -2926 2927
		mu 0 3 1205 1204 1203
		f 3 -2928 2928 2929
		mu 0 3 1205 1203 1206
		f 3 2930 2931 -2930
		mu 0 3 1206 1207 1205
		f 3 -2932 2932 2933
		mu 0 3 1205 1207 1208
		f 3 2934 -2934 2935
		mu 0 3 1209 1205 1208
		f 3 2936 -2936 2937
		mu 0 3 1210 1209 1208
		f 3 -2938 2938 2939
		mu 0 3 1210 1208 1211
		f 3 -2939 2940 2941
		mu 0 3 1211 1208 1212
		f 3 -2942 2942 2943
		mu 0 3 1211 1212 1213
		f 3 2944 2945 -2944
		mu 0 3 1213 1214 1211
		f 3 2946 -2945 2947
		mu 0 3 1215 1214 1213
		f 3 2948 -2948 2949
		mu 0 3 1216 1215 1213
		f 3 2950 -2949 2951
		mu 0 3 1217 1215 1216
		f 3 -2952 2952 2953
		mu 0 3 1217 1216 560
		f 3 2954 -2954 2955
		mu 0 3 1218 1217 560
		f 3 2956 -2955 2957
		mu 0 3 1219 1217 1218
		f 3 -2958 2958 2959
		mu 0 3 1219 1218 531
		f 3 2960 -2960 2961
		mu 0 3 1220 1219 531
		f 3 -2962 2962 2963
		mu 0 3 1220 531 1221
		f 3 2964 2965 -2964
		mu 0 3 1221 1222 1220
		f 3 2966 -2966 2967
		mu 0 3 1223 1220 1222
		f 3 2968 2969 -2968
		mu 0 3 1222 1224 1223
		f 3 2970 -2970 2971
		mu 0 3 1225 1223 1224
		f 3 -2972 2972 2973
		mu 0 3 1225 1224 1226
		f 3 -2973 2974 2975
		mu 0 3 1226 1224 1227
		f 3 -2976 2976 2977
		mu 0 3 1226 1227 1228
		f 3 2978 -2978 2979
		mu 0 3 1229 1226 1228
		f 3 2980 -2980 2981
		mu 0 3 1230 1229 1228
		f 3 2982 -2982 2983
		mu 0 3 1231 1230 1228
		f 3 2984 -2984 2985
		mu 0 3 1232 1231 1228
		f 3 2986 -2986 2987
		mu 0 3 1233 1232 1228
		f 3 2988 -2987 2989
		mu 0 3 1234 1232 1233
		f 3 2990 -2990 2991
		mu 0 3 1235 1234 1233
		f 3 -2992 2992 2993
		mu 0 3 1235 1233 1236
		f 3 2994 2995 -2993
		mu 0 3 1233 1227 1236
		f 3 -2996 2996 2997
		mu 0 3 1236 1227 1222
		f 3 2998 -2998 2999
		mu 0 3 528 1236 1222
		f 3 -3000 3000 3001
		mu 0 3 528 1222 1237
		f 3 3002 3003 -2994
		mu 0 3 1236 525 1235
		f 3 -2991 3004 3005
		mu 0 3 1234 1235 1238
		f 3 -3005 3006 3007
		mu 0 3 1238 1235 524
		f 3 -3008 3008 3009
		mu 0 3 1238 524 1239
		f 3 3010 -3010 3011
		mu 0 3 1240 1238 1239
		f 3 -3012 3012 3013
		mu 0 3 1240 1239 1241
		f 3 3014 3015 -3014
		mu 0 3 1241 1242 1240
		f 3 3016 -3016 3017
		mu 0 3 1243 1240 1242
		f 3 3018 -3018 3019
		mu 0 3 1244 1243 1242
		f 3 3020 -3020 3021
		mu 0 3 1245 1244 1242
		f 3 3022 -3022 3023
		mu 0 3 1246 1245 1242
		f 3 3024 3025 -3024
		mu 0 3 1242 1247 1246
		f 3 3026 -3026 3027
		mu 0 3 1248 1246 1247
		f 3 -3028 3028 3029
		mu 0 3 1248 1247 1249
		f 3 -3030 3030 3031
		mu 0 3 1248 1249 432
		f 3 -3027 3032 3033
		mu 0 3 1246 1248 431
		f 3 3034 3035 -3034
		mu 0 3 431 1250 1246
		f 3 3036 -3036 3037
		mu 0 3 1251 1246 1250
		f 3 3038 -3038 3039
		mu 0 3 1252 1251 1250
		f 3 3040 -3040 3041
		mu 0 3 1253 1252 1250
		f 3 -3041 3042 3043
		mu 0 3 1252 1253 1254
		f 3 3044 3045 -3044
		mu 0 3 1254 1255 1252
		f 3 -3046 3046 3047
		mu 0 3 1252 1255 1256
		f 3 3048 -3047 3049
		mu 0 3 1257 1256 1255
		f 3 3050 -3050 3051
		mu 0 3 1258 1257 1255
		f 3 3052 -3051 3053
		mu 0 3 1259 1257 1258
		f 3 3054 -3054 3055
		mu 0 3 425 1259 1258
		f 3 3056 -3053 3057
		mu 0 3 1260 1257 1259
		f 3 -3058 3058 3059
		mu 0 3 1260 1259 1261
		f 3 3060 -3059 3061
		mu 0 3 1262 1261 1259
		f 3 3062 -3062 3063
		mu 0 3 423 1262 1259
		f 3 3064 3065 -3063
		mu 0 3 423 1263 1262
		f 3 3066 3067 -3066
		mu 0 3 1263 1264 1262
		f 3 -3067 3068 3069
		mu 0 3 1264 1263 422
		f 3 3070 -3070 3071
		mu 0 3 1265 1264 422
		f 3 3072 -3071 3073
		mu 0 3 1266 1264 1265
		f 3 3074 3075 -3074
		mu 0 3 1265 1267 1266
		f 3 3076 3077 -3076
		mu 0 3 1267 1268 1266
		f 3 3078 -3078 3079
		mu 0 3 1269 1266 1268
		f 3 3080 -3080 3081
		mu 0 3 1270 1269 1268
		f 3 3082 -3082 3083
		mu 0 3 1271 1270 1268
		f 3 -3084 3084 3085
		mu 0 3 1271 1268 1272
		f 3 3086 -3086 3087
		mu 0 3 1273 1271 1272
		f 3 3088 3089 -3088
		mu 0 3 1272 1274 1273
		f 3 3090 3091 -3090
		mu 0 3 1274 1275 1273
		f 3 -3092 3092 3093
		mu 0 3 1273 1275 1276
		f 3 3094 -3093 3095
		mu 0 3 1277 1276 1275
		f 3 3096 3097 -3096
		mu 0 3 1275 1278 1277
		f 3 3098 -3098 3099
		mu 0 3 1279 1277 1278
		f 3 3100 -3100 3101
		mu 0 3 1280 1279 1278
		f 3 3102 -3102 3103
		mu 0 3 1281 1280 1278
		f 3 3104 -3104 3105
		mu 0 3 1282 1281 1278
		f 3 -3106 3106 3107
		mu 0 3 1282 1278 1283
		f 3 3108 -3108 3109
		mu 0 3 1284 1282 1283
		f 3 -3110 3110 3111
		mu 0 3 1284 1283 1285
		f 3 3112 -3112 3113
		mu 0 3 1286 1284 1285
		f 3 3114 -3114 3115
		mu 0 3 1287 1286 1285
		f 3 3116 -3116 3117
		mu 0 3 1288 1287 1285
		f 3 3118 3119 -3118
		mu 0 3 1285 1289 1288
		f 3 3120 3121 -3120
		mu 0 3 1289 1290 1288
		f 3 -3122 3122 3123
		mu 0 3 1288 1290 1291
		f 3 -3123 3124 3125
		mu 0 3 1291 1290 1292
		f 3 3126 -3126 3127
		mu 0 3 1293 1291 1292
		f 3 3128 -3128 3129
		mu 0 3 1272 1293 1292
		f 3 3130 -3127 3131
		mu 0 3 1267 1291 1293
		f 3 3132 -3131 3133
		mu 0 3 1294 1291 1267
		f 3 3134 3135 -3133
		mu 0 3 1294 1295 1291
		f 3 3136 -3136 3137
		mu 0 3 1296 1291 1295
		f 3 3138 -3138 3139
		mu 0 3 1297 1296 1295
		f 3 3140 -3140 3141
		mu 0 3 1298 1297 1295
		f 3 3142 -3142 3143
		mu 0 3 1299 1298 1295
		f 3 -3143 3144 3145
		mu 0 3 1298 1299 1300
		f 3 3146 -3145 3147
		mu 0 3 1265 1300 1299
		f 3 -3148 3148 3149
		mu 0 3 1265 1299 1294
		f 3 3150 -3147 3151
		mu 0 3 420 1300 1265
		f 3 -3151 3152 3153
		mu 0 3 1300 420 413
		f 3 3154 3155 -3146
		mu 0 3 1300 411 1298
		f 3 3156 -3141 -3156
		mu 0 3 411 1297 1298
		f 3 3157 3158 -3157
		mu 0 3 411 1301 1297
		f 3 -3159 3159 3160
		mu 0 3 1297 1301 1302
		f 3 3161 -3160 3162
		mu 0 3 1303 1302 1301
		f 3 3163 3164 -3163
		mu 0 3 1301 1304 1303
		f 3 3165 3166 -3165
		mu 0 3 1304 1305 1303
		f 3 -3166 3167 3168
		mu 0 3 1305 1304 408
		f 3 3169 -3169 3170
		mu 0 3 1306 1305 408
		f 3 -3171 3171 3172
		mu 0 3 1306 408 1307
		f 3 3173 3174 -3173
		mu 0 3 1307 1308 1306
		f 3 3175 3176 -3175
		mu 0 3 1308 1309 1306
		f 3 3177 -3177 3178
		mu 0 3 1310 1306 1309
		f 3 3179 3180 -3179
		mu 0 3 1309 1311 1310
		f 3 3181 3182 -3181
		mu 0 3 1311 1312 1310
		f 3 3183 -3183 3184
		mu 0 3 1313 1310 1312
		f 3 3185 -3185 3186
		mu 0 3 1314 1313 1312
		f 3 -3186 3187 3188
		mu 0 3 1313 1314 1315
		f 3 3189 -3189 3190
		mu 0 3 1316 1313 1315
		f 3 3191 3192 -3191
		mu 0 3 1315 1317 1316
		f 3 3193 -3193 3194
		mu 0 3 1318 1316 1317
		f 3 3195 -3195 3196
		mu 0 3 1319 1318 1317
		f 3 3197 -3197 3198
		mu 0 3 1320 1319 1317
		f 3 3199 -3199 3200
		mu 0 3 1321 1320 1317
		f 3 -3200 3201 3202
		mu 0 3 1320 1321 1322
		f 3 3203 -3202 3204
		mu 0 3 1323 1322 1321
		f 3 3205 -3205 3206
		mu 0 3 1324 1323 1321
		f 3 -3207 3207 3208
		mu 0 3 1324 1321 1314
		f 3 -3209 3209 3210
		mu 0 3 1324 1314 1325
		f 3 -3211 3211 3212
		mu 0 3 1324 1325 1326
		f 3 -3213 3213 3214
		mu 0 3 1324 1326 1327
		f 3 3215 -3215 3216
		mu 0 3 1328 1324 1327
		f 3 3217 -3217 3218
		mu 0 3 1329 1328 1327
		f 3 3219 -3219 3220
		mu 0 3 1330 1329 1327
		f 3 -3220 3221 3222
		mu 0 3 1329 1330 1331
		f 3 3223 -3223 3224
		mu 0 3 1332 1329 1331
		f 3 3225 -3225 3226
		mu 0 3 1333 1332 1331
		f 3 3227 -3227 3228
		mu 0 3 1334 1333 1331
		f 3 3229 -3229 3230
		mu 0 3 1335 1334 1331
		f 3 3231 -3230 3232
		mu 0 3 1336 1334 1335
		f 3 -3233 3233 3234
		mu 0 3 1336 1335 373
		f 3 3235 -3235 3236
		mu 0 3 1337 1336 373
		f 3 3237 3238 -3237
		mu 0 3 373 1338 1337
		f 3 -3239 3239 3240
		mu 0 3 1337 1338 1339
		f 3 3241 3242 -3241
		mu 0 3 1339 1340 1337
		f 3 3243 -3242 3244
		mu 0 3 1341 1340 1339
		f 3 -3245 3245 3246
		mu 0 3 1341 1339 1342
		f 3 3247 3248 -3247
		mu 0 3 1342 1343 1341
		f 3 3249 3250 -3248
		mu 0 3 1342 1344 1343
		f 3 -3251 3251 3252
		mu 0 3 1343 1344 1345
		f 3 -3253 3253 3254
		mu 0 3 1343 1345 1346
		f 3 3255 3256 -3254
		mu 0 3 1345 1347 1346
		f 3 3257 3258 -3257
		mu 0 3 1347 1348 1346
		f 3 3259 3260 -3258
		mu 0 3 1347 1349 1348
		f 3 3261 3262 -3261
		mu 0 3 1349 1350 1348
		f 3 3263 3264 -3263
		mu 0 3 1350 1351 1348
		f 3 -3265 3265 3266
		mu 0 3 1348 1351 1352
		f 3 -3267 3267 3268
		mu 0 3 1348 1352 1336
		f 3 -3268 3269 3270
		mu 0 3 1336 1352 1353
		f 3 -3270 3271 3272
		mu 0 3 1353 1352 1354
		f 3 -3273 3273 3274
		mu 0 3 1353 1354 1333
		f 3 3275 -3274 3276
		mu 0 3 1355 1333 1354
		f 3 3277 3278 -3277
		mu 0 3 1354 1356 1355
		f 3 -3279 3279 3280
		mu 0 3 1355 1356 1322
		f 3 -3281 3281 3282
		mu 0 3 1355 1322 1332
		f 3 3283 -3278 3284
		mu 0 3 1357 1356 1354
		f 3 3285 -3285 3286
		mu 0 3 1358 1357 1354
		f 3 -3287 3287 3288
		mu 0 3 1358 1354 1359
		f 3 3289 3290 -3289
		mu 0 3 1359 1360 1358
		f 3 3291 3292 -3291
		mu 0 3 1360 1361 1358
		f 3 3293 3294 -3292
		mu 0 3 1360 1362 1361
		f 3 3295 -3295 3296
		mu 0 3 1363 1361 1362
		f 3 3297 -3297 3298
		mu 0 3 1364 1363 1362
		f 3 3299 -3299 3300
		mu 0 3 1365 1364 1362
		f 3 -3301 3301 3302
		mu 0 3 1365 1362 1366
		f 3 -3303 3303 3304
		mu 0 3 1365 1366 1367
		f 3 -3304 3305 3306
		mu 0 3 1367 1366 1360
		f 3 3307 -3305 3308
		mu 0 3 1368 1365 1367
		f 3 -3309 3309 3310
		mu 0 3 1368 1367 1359
		f 3 -3311 3311 3312
		mu 0 3 1368 1359 1369
		f 3 3313 -3312 3314
		mu 0 3 1370 1369 1359
		f 3 3315 -3314 3316
		mu 0 3 1351 1369 1370
		f 3 3317 3318 -3316
		mu 0 3 1351 1371 1369
		f 3 3319 3320 -3319
		mu 0 3 1371 1372 1369
		f 3 3321 -3320 3322
		mu 0 3 1373 1372 1371
		f 3 3323 -3323 3324
		mu 0 3 1374 1373 1371
		f 3 3325 3326 -3324
		mu 0 3 1374 1375 1373
		f 3 3327 3328 -3326
		mu 0 3 1374 1376 1375
		f 3 3329 -3329 3330
		mu 0 3 1377 1375 1376
		f 3 3331 3332 -3331
		mu 0 3 1376 1378 1377
		f 3 -3333 3333 3334
		mu 0 3 1377 1378 1379
		f 3 3335 3336 -3335
		mu 0 3 1379 1380 1377
		f 3 3337 -3336 3338
		mu 0 3 1381 1380 1379
		f 3 -3339 3339 3340
		mu 0 3 1381 1379 1382
		f 3 3341 3342 -3341
		mu 0 3 1382 1383 1381
		f 3 3343 3344 -3343
		mu 0 3 1383 1384 1381
		f 3 -3345 3345 3346
		mu 0 3 1381 1384 1385
		f 3 -3347 3347 3348
		mu 0 3 1381 1385 1386
		f 3 3349 3350 -3348
		mu 0 3 1385 1387 1386
		f 3 -3351 3351 3352
		mu 0 3 1386 1387 1388
		f 3 3353 -3353 3354
		mu 0 3 1389 1386 1388
		f 3 -3355 3355 3356
		mu 0 3 1389 1388 1390
		f 3 3357 3358 -3357
		mu 0 3 1390 1391 1389
		f 3 3359 -3359 3360
		mu 0 3 1392 1389 1391
		f 3 3361 3362 -3361
		mu 0 3 1391 1393 1392
		f 3 -3363 3363 3364
		mu 0 3 1392 1393 1394
		f 3 3365 -3365 3366
		mu 0 3 1395 1392 1394
		f 3 -3367 3367 3368
		mu 0 3 1395 1394 1396
		f 3 -3369 3369 3370
		mu 0 3 1395 1396 1397
		f 3 3371 3372 -3370
		mu 0 3 1396 1365 1397
		f 3 3373 3374 -3371
		mu 0 3 1397 1398 1395
		f 3 -3374 3375 3376
		mu 0 3 1398 1397 1372
		f 3 3377 -3377 3378
		mu 0 3 1375 1398 1372
		f 3 3379 3380 -3378
		mu 0 3 1375 1380 1398
		f 3 3381 3382 -3381
		mu 0 3 1380 1392 1398
		f 3 3383 -3376 3384
		mu 0 3 1368 1372 1397
		f 3 3385 3386 -3368
		mu 0 3 1394 1399 1396
		f 3 3387 3388 -3387
		mu 0 3 1399 1400 1396
		f 3 -3389 3389 3390
		mu 0 3 1396 1400 1364
		f 3 3391 3392 -3390
		mu 0 3 1400 1401 1364
		f 3 3393 3394 -3392
		mu 0 3 1400 1402 1401
		f 3 -3395 3395 3396
		mu 0 3 1401 1402 1403
		f 3 -3397 3397 3398
		mu 0 3 1401 1403 1404
		f 3 3399 3400 -3398
		mu 0 3 1403 1405 1404
		f 3 3401 3402 -3401
		mu 0 3 1405 1406 1404
		f 3 -3403 3403 3404
		mu 0 3 1404 1406 1407
		f 3 3405 -3405 3406
		mu 0 3 1363 1404 1407
		f 3 3407 3408 -3404
		mu 0 3 1406 1408 1407
		f 3 -3409 3409 3410
		mu 0 3 1407 1408 1409
		f 3 -3410 3411 3412
		mu 0 3 1409 1408 1410
		f 3 3413 -3413 3414
		mu 0 3 1411 1409 1410
		f 3 -3415 3415 3416
		mu 0 3 1411 1410 1412
		f 3 3417 3418 -3416
		mu 0 3 1410 1413 1412
		f 3 -3419 3419 3420
		mu 0 3 1412 1413 1414
		f 3 3421 3422 -3420
		mu 0 3 1413 1415 1414
		f 3 3423 -3423 3424
		mu 0 3 1416 1414 1415
		f 3 3425 3426 -3425
		mu 0 3 1415 1417 1416
		f 3 -3427 3427 3428
		mu 0 3 1416 1417 1316
		f 3 3429 3430 -3426
		mu 0 3 1415 1418 1417
		f 3 -3431 3431 3432
		mu 0 3 1417 1418 1419
		f 3 3433 3434 -3432
		mu 0 3 1418 1420 1419
		f 3 -3435 3435 3436
		mu 0 3 1419 1420 1421
		f 3 3437 3438 -3436
		mu 0 3 1420 1422 1421
		f 3 -3439 3439 3440
		mu 0 3 1421 1422 1423
		f 3 3441 -3441 3442
		mu 0 3 1424 1421 1423
		f 3 3443 -3443 3444
		mu 0 3 1425 1424 1423
		f 3 3445 -3445 3446
		mu 0 3 1426 1425 1423
		f 3 3447 -3446 3448
		mu 0 3 1427 1425 1426
		f 3 3449 -3449 3450
		mu 0 3 1428 1427 1426
		f 3 3451 -3451 3452
		mu 0 3 1429 1428 1426
		f 3 3453 -3453 3454
		mu 0 3 1422 1429 1426
		f 3 3455 3456 -3452
		mu 0 3 1429 1430 1428
		f 3 3457 3458 -3457
		mu 0 3 1430 1431 1428
		f 3 3459 3460 -3459
		mu 0 3 1431 1432 1428
		f 3 -3461 3461 3462
		mu 0 3 1428 1432 1287
		f 3 3463 -3460 3464
		mu 0 3 1433 1432 1431
		f 3 3465 -3464 3466
		mu 0 3 1434 1432 1433
		f 3 -3467 3467 3468
		mu 0 3 1434 1433 1435
		f 3 -3468 3469 3470
		mu 0 3 1435 1433 1430
		f 3 3471 -3471 3472
		mu 0 3 1436 1435 1430
		f 3 -3473 3473 3474
		mu 0 3 1436 1430 1420
		f 3 3475 -3472 3476
		mu 0 3 1418 1435 1436
		f 3 3477 -3469 3478
		mu 0 3 1437 1434 1435
		f 3 -3479 3479 3480
		mu 0 3 1437 1435 1415
		f 3 -3481 3481 3482
		mu 0 3 1437 1415 1438
		f 3 3483 -3483 3484
		mu 0 3 1410 1437 1438
		f 3 3485 3486 -3478
		mu 0 3 1437 1439 1434
		f 3 3487 3488 -3487
		mu 0 3 1439 1286 1434
		f 3 -3488 3489 3490
		mu 0 3 1286 1439 1440
		f 3 3491 -3490 3492
		mu 0 3 1441 1440 1439
		f 3 3493 3494 -3493
		mu 0 3 1439 1442 1441
		f 3 3495 3496 -3495
		mu 0 3 1442 1443 1441
		f 3 -3497 3497 3498
		mu 0 3 1441 1443 1444
		f 3 3499 -3498 3500
		mu 0 3 1445 1444 1443
		f 3 3501 3502 -3501
		mu 0 3 1443 1446 1445
		f 3 3503 3504 -3503
		mu 0 3 1446 1447 1445
		f 3 -3505 3505 3506
		mu 0 3 1445 1447 1448
		f 3 3507 3508 -3506
		mu 0 3 1447 1449 1448
		f 3 -3509 3509 3510
		mu 0 3 1448 1449 1450
		f 3 3511 -3511 3512
		mu 0 3 1280 1448 1450
		f 3 3513 3514 -3513
		mu 0 3 1450 1451 1280
		f 3 -3515 3515 3516
		mu 0 3 1280 1451 1452
		f 3 3517 3518 -3516
		mu 0 3 1451 1453 1452
		f 3 -3519 3519 3520
		mu 0 3 1452 1453 1454
		f 3 -3521 3521 3522
		mu 0 3 1452 1454 1277
		f 3 3523 3524 -3520
		mu 0 3 1453 1455 1454
		f 3 -3525 3525 3526
		mu 0 3 1454 1455 1456
		f 3 3527 3528 -3526
		mu 0 3 1455 1457 1456
		f 3 3529 3530 -3529
		mu 0 3 1457 1458 1456
		f 3 -3531 3531 3532
		mu 0 3 1456 1458 1459
		f 3 -3533 3533 3534
		mu 0 3 1456 1459 1460
		f 3 -3534 3535 3536
		mu 0 3 1460 1459 1461
		f 3 -3537 3537 3538
		mu 0 3 1460 1461 1462
		f 3 3539 3540 -3538
		mu 0 3 1461 1463 1462
		f 3 3541 3542 -3541
		mu 0 3 1463 1464 1462
		f 3 -3543 3543 3544
		mu 0 3 1462 1464 1465
		f 3 3545 3546 -3544
		mu 0 3 1464 1466 1465
		f 3 -3547 3547 3548
		mu 0 3 1465 1466 1467
		f 3 3549 -3548 3550
		mu 0 3 1468 1467 1466
		f 3 3551 -3551 3552
		mu 0 3 1469 1468 1466
		f 3 3553 -3553 3554
		mu 0 3 1470 1469 1466
		f 3 -3555 3555 3556
		mu 0 3 1470 1466 1471
		f 3 3557 3558 -3557
		mu 0 3 1471 1472 1470
		f 3 3559 3560 -3559
		mu 0 3 1472 1473 1470
		f 3 3561 3562 -3561
		mu 0 3 1473 1474 1470
		f 3 -3562 3563 3564
		mu 0 3 1474 1473 1475
		f 3 -3564 3565 3566
		mu 0 3 1475 1473 1476
		f 3 3567 3568 -3567
		mu 0 3 1476 1477 1475
		f 3 3569 3570 -3569
		mu 0 3 1477 1478 1475
		f 3 3571 -3571 3572
		mu 0 3 1479 1475 1478
		f 3 -3573 3573 3574
		mu 0 3 1479 1478 1257
		f 3 -3570 3575 3576
		mu 0 3 1478 1477 1251
		f 3 -3577 3577 3578
		mu 0 3 1478 1251 1256
		f 3 3579 3580 -3576
		mu 0 3 1477 1245 1251
		f 3 -3580 3581 3582
		mu 0 3 1245 1477 1480
		f 3 3583 3584 -3583
		mu 0 3 1480 1481 1245
		f 3 3585 3586 -3584
		mu 0 3 1480 1482 1481
		f 3 3587 -3587 3588
		mu 0 3 1243 1481 1482
		f 3 -3589 3589 3590
		mu 0 3 1243 1482 1234
		f 3 3591 3592 -3586
		mu 0 3 1480 1231 1482
		f 3 -3592 3593 3594
		mu 0 3 1231 1480 1483
		f 3 -3594 -3582 3595
		mu 0 3 1483 1480 1477
		f 3 3596 -3596 -3568
		mu 0 3 1476 1483 1477
		f 3 3597 -3597 3598
		mu 0 3 1484 1483 1476
		f 3 3599 3600 -3599
		mu 0 3 1476 1472 1484
		f 3 3601 3602 -3601
		mu 0 3 1472 1485 1484
		f 3 -3603 3603 3604
		mu 0 3 1484 1485 1486
		f 3 3605 3606 -3604
		mu 0 3 1485 1487 1486
		f 3 -3607 3607 3608
		mu 0 3 1486 1487 1229
		f 3 3609 -3608 3610
		mu 0 3 1488 1229 1487
		f 3 3611 3612 -3611
		mu 0 3 1487 1489 1488
		f 3 3613 -3613 3614
		mu 0 3 1490 1488 1489
		f 3 -3615 3615 3616
		mu 0 3 1490 1489 1491
		f 3 -3617 3617 3618
		mu 0 3 1490 1491 1472
		f 3 3619 3620 -3619
		mu 0 3 1472 1492 1490
		f 3 3621 3622 -3621
		mu 0 3 1492 1493 1490
		f 3 -3623 3623 3624
		mu 0 3 1490 1493 1494
		f 3 3625 -3624 3626
		mu 0 3 1495 1494 1493
		f 3 3627 -3627 3628
		mu 0 3 1496 1495 1493
		f 3 3629 3630 -3628
		mu 0 3 1496 1497 1495
		f 3 3631 3632 -3631
		mu 0 3 1497 1471 1495
		f 3 3633 -3633 3634
		mu 0 3 1464 1495 1471
		f 3 3635 3636 -3634
		mu 0 3 1464 1498 1495
		f 3 3637 3638 -3637
		mu 0 3 1498 1499 1495
		f 3 -3639 3639 3640
		mu 0 3 1495 1499 1500
		f 3 3641 3642 -3640
		mu 0 3 1499 1219 1500
		f 3 3643 -3643 3644
		mu 0 3 1501 1500 1219
		f 3 -3644 3645 3646
		mu 0 3 1500 1501 1225
		f 3 -3647 3647 3648
		mu 0 3 1500 1225 1488
		f 3 3649 -3649 3650
		mu 0 3 1494 1500 1488
		f 3 3651 -3642 3652
		mu 0 3 1214 1219 1499
		f 3 -3653 3653 3654
		mu 0 3 1214 1499 1502
		f 3 3655 -3654 3656
		mu 0 3 1503 1502 1499
		f 3 -3656 3657 3658
		mu 0 3 1502 1503 1504
		f 3 -3658 3659 3660
		mu 0 3 1504 1503 1505
		f 3 3661 -3660 3662
		mu 0 3 1506 1505 1503
		f 3 3663 -3663 3664
		mu 0 3 1507 1506 1503
		f 3 -3665 3665 3666
		mu 0 3 1507 1503 1508
		f 3 -3666 3667 3668
		mu 0 3 1508 1503 1498
		f 3 -3669 3669 3670
		mu 0 3 1508 1498 1463
		f 3 -3667 3671 3672
		mu 0 3 1507 1508 1461
		f 3 -3673 3673 -3664
		mu 0 3 1507 1461 1506
		f 3 3674 -3662 3675
		mu 0 3 1458 1505 1506
		f 3 3676 -3661 -3675
		mu 0 3 1458 1504 1505
		f 3 3677 3678 -3677
		mu 0 3 1458 1509 1504
		f 3 -3679 3679 3680
		mu 0 3 1504 1509 1510
		f 3 3681 -3680 3682
		mu 0 3 1511 1510 1509
		f 3 3683 -3683 3684
		mu 0 3 1512 1511 1509
		f 3 -3685 3685 3686
		mu 0 3 1512 1509 1457
		f 3 3687 3688 -3687
		mu 0 3 1457 1513 1512
		f 3 -3689 3689 3690
		mu 0 3 1512 1513 1514
		f 3 3691 -3690 3692
		mu 0 3 1515 1514 1513
		f 3 3693 3694 -3693
		mu 0 3 1513 1516 1515
		f 3 -3695 3695 3696
		mu 0 3 1515 1516 1517
		f 3 -3696 3697 3698
		mu 0 3 1517 1516 1451
		f 3 -3694 3699 3700
		mu 0 3 1516 1513 1455
		f 3 -3692 -3697 3701
		mu 0 3 1514 1515 1517
		f 3 3702 -3702 3703
		mu 0 3 1450 1514 1517
		f 3 3704 3705 -3691
		mu 0 3 1514 1518 1512
		f 3 -3706 3706 3707
		mu 0 3 1512 1518 1519
		f 3 3708 3709 -3707
		mu 0 3 1518 1520 1519
		f 3 -3710 3710 3711
		mu 0 3 1519 1520 1521
		f 3 -3711 3712 3713
		mu 0 3 1521 1520 1522
		f 3 3714 3715 -3713
		mu 0 3 1520 1523 1522
		f 3 -3716 3716 3717
		mu 0 3 1522 1523 1524
		f 3 3718 3719 -3717
		mu 0 3 1523 1525 1524
		f 3 -3720 3720 3721
		mu 0 3 1524 1525 1526
		f 3 -3722 3722 3723
		mu 0 3 1524 1526 1527
		f 3 -3723 3724 3725
		mu 0 3 1527 1526 1528
		f 3 3726 -3725 3727
		mu 0 3 1529 1528 1526
		f 3 3728 3729 -3728
		mu 0 3 1526 1530 1529
		f 3 -3730 3730 3731
		mu 0 3 1529 1530 1192
		f 3 3732 -3729 3733
		mu 0 3 1531 1530 1526
		f 3 3734 3735 -3733
		mu 0 3 1531 1532 1530
		f 3 3736 3737 -3736
		mu 0 3 1532 1191 1530
		f 3 -3737 3738 3739
		mu 0 3 1191 1532 1533
		f 3 -3740 3740 3741
		mu 0 3 1191 1533 1534
		f 3 3742 3743 -3741
		mu 0 3 1533 1188 1534
		f 3 3744 3745 -3743
		mu 0 3 1533 1535 1188
		f 3 3746 -3746 3747
		mu 0 3 1536 1188 1535
		f 3 3748 -3748 3749
		mu 0 3 1537 1536 1535
		f 3 3750 -3750 3751
		mu 0 3 1538 1537 1535
		f 3 3752 -3752 3753
		mu 0 3 1539 1538 1535
		f 3 3754 -3754 3755
		mu 0 3 1540 1539 1535
		f 3 3756 -3755 3757
		mu 0 3 1541 1539 1540
		f 3 3758 -3758 3759
		mu 0 3 1542 1541 1540
		f 3 -3760 3760 3761
		mu 0 3 1542 1540 1532
		f 3 -3762 3762 3763
		mu 0 3 1542 1532 1543
		f 3 3764 3765 -3764
		mu 0 3 1543 1544 1542
		f 3 3766 3767 -3766
		mu 0 3 1544 1545 1542
		f 3 3768 -3768 3769
		mu 0 3 1546 1542 1545
		f 3 -3770 3770 3771
		mu 0 3 1546 1545 1547
		f 3 -3771 3772 3773
		mu 0 3 1547 1545 1548
		f 3 3774 3775 -3774
		mu 0 3 1548 1549 1547
		f 3 3776 -3776 3777
		mu 0 3 1550 1547 1549
		f 3 3778 3779 -3778
		mu 0 3 1549 1551 1550
		f 3 -3780 3780 3781
		mu 0 3 1550 1551 1552
		f 3 3782 3783 -3781
		mu 0 3 1551 1553 1552
		f 3 3784 -3784 3785
		mu 0 3 1554 1552 1553
		f 3 3786 3787 -3786
		mu 0 3 1553 1555 1554
		f 3 3788 3789 -3788
		mu 0 3 1555 1556 1554
		f 3 3790 -3790 3791
		mu 0 3 1557 1554 1556
		f 3 -3792 3792 3793
		mu 0 3 1557 1556 1558
		f 3 3794 3795 -3793
		mu 0 3 1556 1559 1558
		f 3 3796 -3796 3797
		mu 0 3 1560 1558 1559
		f 3 -3798 3798 3799
		mu 0 3 1560 1559 1561
		f 3 3800 -3800 3801
		mu 0 3 1562 1560 1561
		f 3 -3802 3802 3803
		mu 0 3 1562 1561 1563
		f 3 3804 -3804 3805
		mu 0 3 1390 1562 1563
		f 3 -3803 3806 3807
		mu 0 3 1563 1561 1399
		f 3 3808 3809 -3807
		mu 0 3 1561 1564 1399
		f 3 3810 -3808 3811
		mu 0 3 1393 1563 1399
		f 3 3812 -3801 3813
		mu 0 3 1388 1560 1562
		f 3 -3799 3814 -3809
		mu 0 3 1561 1559 1564
		f 3 3815 3816 -3815
		mu 0 3 1559 1565 1564
		f 3 3817 3818 -3817
		mu 0 3 1565 1402 1564
		f 3 3819 3820 -3818
		mu 0 3 1565 1566 1402
		f 3 -3821 3821 3822
		mu 0 3 1402 1566 1567
		f 3 3823 3824 -3822
		mu 0 3 1566 1568 1567
		f 3 -3825 3825 3826
		mu 0 3 1567 1568 1442
		f 3 -3827 3827 3828
		mu 0 3 1567 1442 1405
		f 3 3829 3830 -3826
		mu 0 3 1568 1569 1442
		f 3 3831 -3830 3832
		mu 0 3 1570 1569 1568
		f 3 3833 -3833 3834
		mu 0 3 1571 1570 1568
		f 3 3835 -3835 3836
		mu 0 3 1555 1571 1568
		f 3 -3836 3837 3838
		mu 0 3 1571 1555 1551
		f 3 3839 3840 -3834
		mu 0 3 1571 1549 1570
		f 3 3841 3842 -3832
		mu 0 3 1570 1572 1569
		f 3 3843 3844 -3843
		mu 0 3 1572 1573 1569
		f 3 3845 -3845 3846
		mu 0 3 1446 1569 1573
		f 3 3847 3848 -3844
		mu 0 3 1572 1574 1573;
	setAttr ".fc[2000:2499]"
		f 3 3849 3850 -3849
		mu 0 3 1574 1575 1573
		f 3 3851 3852 -3851
		mu 0 3 1575 1576 1573
		f 3 3853 3854 -3853
		mu 0 3 1576 1577 1573
		f 3 -3855 3855 3856
		mu 0 3 1573 1577 1447
		f 3 -3854 3857 3858
		mu 0 3 1577 1576 1578
		f 3 -3858 3859 3860
		mu 0 3 1578 1576 1579
		f 3 3861 3862 -3860
		mu 0 3 1576 1580 1579
		f 3 3863 -3863 3864
		mu 0 3 1581 1579 1580
		f 3 3865 -3865 3866
		mu 0 3 1544 1581 1580
		f 3 -3867 3867 3868
		mu 0 3 1544 1580 1574
		f 3 3869 -3869 3870
		mu 0 3 1582 1544 1574
		f 3 -3864 3871 3872
		mu 0 3 1579 1581 1525
		f 3 3873 -3872 3874
		mu 0 3 1531 1525 1581
		f 3 3875 3876 -3875
		mu 0 3 1581 1543 1531
		f 3 -3861 3877 3878
		mu 0 3 1578 1579 1523
		f 3 3879 3880 -3859
		mu 0 3 1578 1583 1577
		f 3 -3881 3881 3882
		mu 0 3 1577 1583 1449
		f 3 3883 -3882 3884
		mu 0 3 1514 1449 1583
		f 3 -3880 3885 3886
		mu 0 3 1583 1578 1520
		f 3 -3852 3887 -3862
		mu 0 3 1576 1575 1580
		f 3 -3888 -3850 -3868
		mu 0 3 1580 1575 1574
		f 3 -3848 3888 -3871
		mu 0 3 1574 1572 1582
		f 3 3889 3890 -3889
		mu 0 3 1572 1584 1582
		f 3 -3891 3891 3892
		mu 0 3 1582 1584 1545
		f 3 3893 -3890 -3842
		mu 0 3 1570 1584 1572
		f 3 3894 -3894 3895
		mu 0 3 1548 1584 1570
		f 3 -3837 -3824 3896
		mu 0 3 1555 1568 1566
		f 3 3897 -3897 -3820
		mu 0 3 1565 1555 1566
		f 3 3898 -3797 3899
		mu 0 3 1585 1558 1560
		f 3 -3900 3900 3901
		mu 0 3 1585 1560 1387
		f 3 -3902 3902 3903
		mu 0 3 1585 1387 1586
		f 3 3904 3905 -3904
		mu 0 3 1586 1587 1585
		f 3 3906 -3905 3907
		mu 0 3 1588 1587 1586
		f 3 -3908 3908 3909
		mu 0 3 1588 1586 1589
		f 3 3910 3911 -3909
		mu 0 3 1586 1590 1589
		f 3 3912 3913 -3912
		mu 0 3 1590 1385 1589
		f 3 -3910 3914 3915
		mu 0 3 1588 1589 1591
		f 3 3916 3917 -3915
		mu 0 3 1589 1592 1591
		f 3 3918 3919 -3918
		mu 0 3 1592 1593 1591
		f 3 -3920 3920 3921
		mu 0 3 1591 1593 1130
		f 3 3922 -3922 3923
		mu 0 3 1594 1591 1130
		f 3 3924 3925 -3924
		mu 0 3 1130 1595 1594
		f 3 3926 -3926 3927
		mu 0 3 1596 1594 1595
		f 3 3928 -3928 3929
		mu 0 3 1597 1596 1595
		f 3 3930 -3930 3931
		mu 0 3 1140 1597 1595
		f 3 -3931 3932 3933
		mu 0 3 1597 1140 1187
		f 3 3934 -3934 3935
		mu 0 3 1536 1597 1187
		f 3 3936 3937 -3935
		mu 0 3 1536 1598 1597
		f 3 3938 -3929 -3938
		mu 0 3 1598 1596 1597
		f 3 -3939 3939 3940
		mu 0 3 1596 1598 1599
		f 3 3941 3942 -3940
		mu 0 3 1598 1600 1599
		f 3 -3943 3943 3944
		mu 0 3 1599 1600 1601
		f 3 -3945 3945 3946
		mu 0 3 1599 1601 1594
		f 3 3947 3948 -3946
		mu 0 3 1601 1588 1594
		f 3 3949 3950 -3944
		mu 0 3 1600 1602 1601
		f 3 -3951 3951 3952
		mu 0 3 1601 1602 1587
		f 3 3953 -3952 3954
		mu 0 3 1557 1587 1602
		f 3 3955 -3955 3956
		mu 0 3 1603 1557 1602
		f 3 3957 -3957 3958
		mu 0 3 1604 1603 1602
		f 3 3959 3960 -3958
		mu 0 3 1604 1605 1603
		f 3 3961 3962 -3961
		mu 0 3 1605 1552 1603
		f 3 3963 -3960 3964
		mu 0 3 1537 1605 1604
		f 3 -3965 3965 3966
		mu 0 3 1537 1604 1598
		f 3 -3959 -3950 3967
		mu 0 3 1604 1602 1600
		f 3 -3968 -3942 -3966
		mu 0 3 1604 1600 1598
		f 3 -3947 -3927 -3941
		mu 0 3 1599 1594 1596
		f 3 3968 3969 -3919
		mu 0 3 1592 1123 1593
		f 3 -3970 3970 3971
		mu 0 3 1593 1123 1126
		f 3 3972 -3917 3973
		mu 0 3 1606 1592 1589
		f 3 3974 3975 -3974
		mu 0 3 1589 1384 1606
		f 3 3976 -3976 3977
		mu 0 3 1607 1606 1384
		f 3 3978 3979 -3977
		mu 0 3 1607 1608 1606
		f 3 -3980 3980 3981
		mu 0 3 1606 1608 1609
		f 3 3982 3983 -3981
		mu 0 3 1608 1610 1609
		f 3 -3984 3984 3985
		mu 0 3 1609 1610 1122
		f 3 -3986 3986 3987
		mu 0 3 1609 1122 1592
		f 3 3988 3989 -3983
		mu 0 3 1608 1611 1610
		f 3 3990 3991 -3990
		mu 0 3 1611 1612 1610
		f 3 -3992 3992 3993
		mu 0 3 1610 1612 1613
		f 3 3994 -3993 3995
		mu 0 3 1614 1613 1612
		f 3 3996 -3996 3997
		mu 0 3 1615 1614 1612
		f 3 3998 3999 -3997
		mu 0 3 1615 1616 1614
		f 3 -4000 4000 4001
		mu 0 3 1614 1616 1617
		f 3 4002 4003 -4001
		mu 0 3 1616 1618 1617
		f 3 -4004 4004 4005
		mu 0 3 1617 1618 1619
		f 3 4006 -4005 4007
		mu 0 3 1620 1619 1618
		f 3 -4008 4008 4009
		mu 0 3 1620 1618 1621
		f 3 4010 4011 -4009
		mu 0 3 1618 1622 1621
		f 3 -4012 4012 4013
		mu 0 3 1621 1622 1623
		f 3 4014 -4014 4015
		mu 0 3 1624 1621 1623
		f 3 -4016 4016 4017
		mu 0 3 1624 1623 1625
		f 3 -4017 4018 4019
		mu 0 3 1625 1623 1626
		f 3 -4020 4020 4021
		mu 0 3 1625 1626 1627
		f 3 4022 -4021 4023
		mu 0 3 1628 1627 1626
		f 3 -4024 4024 4025
		mu 0 3 1628 1626 1629
		f 3 4026 -4026 4027
		mu 0 3 1630 1628 1629
		f 3 -4028 4028 4029
		mu 0 3 1630 1629 1631
		f 3 4030 -4030 4031
		mu 0 3 1632 1630 1631
		f 3 -4032 4032 4033
		mu 0 3 1632 1631 1633
		f 3 4034 -4034 4035
		mu 0 3 1634 1632 1633
		f 3 4036 4037 -4036
		mu 0 3 1633 364 1634
		f 3 4038 4039 -4037
		mu 0 3 1633 1635 364
		f 3 4040 -4035 4041
		mu 0 3 1636 1632 1634
		f 3 4042 4043 -4042
		mu 0 3 1634 358 1636
		f 3 4044 -4043 4045
		mu 0 3 363 358 1634
		f 3 -4041 4046 4047
		mu 0 3 1632 1636 1637
		f 3 4048 -4047 4049
		mu 0 3 1638 1637 1636
		f 3 4050 4051 -4050
		mu 0 3 1636 1627 1638
		f 3 -4051 4052 4053
		mu 0 3 1627 1636 357
		f 3 -4049 4054 4055
		mu 0 3 1637 1638 1630
		f 3 -4033 4056 -4039
		mu 0 3 1633 1631 1635
		f 3 4057 4058 -4057
		mu 0 3 1631 1639 1635
		f 3 4059 4060 -4059
		mu 0 3 1639 1640 1635
		f 3 4061 4062 -4061
		mu 0 3 1640 1641 1635
		f 3 -4063 4063 4064
		mu 0 3 1635 1641 367
		f 3 4065 4066 -4064
		mu 0 3 1641 1642 367
		f 3 4067 4068 -4067
		mu 0 3 1642 1338 367
		f 3 -4069 4069 4070
		mu 0 3 367 1338 371
		f 3 4071 4072 -4068
		mu 0 3 1642 1342 1338
		f 3 4073 -4072 -4066
		mu 0 3 1641 1342 1642
		f 3 4074 -4074 4075
		mu 0 3 1643 1342 1641
		f 3 4076 -4076 4077
		mu 0 3 1644 1643 1641
		f 3 4078 -4078 4079
		mu 0 3 1645 1644 1641
		f 3 4080 4081 -4079
		mu 0 3 1645 1646 1644
		f 3 -4081 4082 4083
		mu 0 3 1646 1645 1647
		f 3 4084 -4083 4085
		mu 0 3 1639 1647 1645
		f 3 4086 -4084 4087
		mu 0 3 1629 1646 1647
		f 3 -4087 4088 4089
		mu 0 3 1646 1629 1648
		f 3 4090 4091 -4090
		mu 0 3 1648 1649 1646
		f 3 4092 -4092 4093
		mu 0 3 1643 1646 1649
		f 3 -4094 4094 4095
		mu 0 3 1643 1649 1344
		f 3 4096 4097 -4095
		mu 0 3 1649 1347 1344
		f 3 4098 4099 -4097
		mu 0 3 1649 1650 1347
		f 3 -4100 4100 4101
		mu 0 3 1347 1650 1651
		f 3 4102 4103 -4101
		mu 0 3 1650 1652 1651
		f 3 4104 4105 -4104
		mu 0 3 1652 1349 1651
		f 3 4106 4107 -4103
		mu 0 3 1650 1653 1652
		f 3 4108 4109 -4108
		mu 0 3 1653 1654 1652
		f 3 -4110 4110 4111
		mu 0 3 1652 1654 1655
		f 3 4112 4113 -4111
		mu 0 3 1654 1656 1655
		f 3 -4114 4114 4115
		mu 0 3 1655 1656 1657
		f 3 -4115 4116 4117
		mu 0 3 1657 1656 1658
		f 3 -4117 4118 4119
		mu 0 3 1658 1656 1659
		f 3 4120 -4120 4121
		mu 0 3 1660 1658 1659
		f 3 4122 -4122 4123
		mu 0 3 1661 1660 1659
		f 3 -4123 4124 4125
		mu 0 3 1660 1661 1662
		f 3 -4125 4126 4127
		mu 0 3 1662 1661 1663
		f 3 4128 4129 -4127
		mu 0 3 1661 1664 1663
		f 3 4130 -4130 4131
		mu 0 3 1665 1663 1664
		f 3 -4132 4132 4133
		mu 0 3 1665 1664 1653
		f 3 -4134 4134 4135
		mu 0 3 1665 1653 1666
		f 3 -4136 4136 4137
		mu 0 3 1665 1666 1667
		f 3 4138 -4137 4139
		mu 0 3 1668 1667 1666
		f 3 4140 -4139 4141
		mu 0 3 1669 1667 1668
		f 3 -4142 4142 4143
		mu 0 3 1669 1668 1649
		f 3 4144 4145 -4141
		mu 0 3 1669 1670 1667
		f 3 4146 4147 -4146
		mu 0 3 1670 1671 1667
		f 3 4148 4149 -4148
		mu 0 3 1671 1662 1667
		f 3 4150 4151 -4149
		mu 0 3 1671 1672 1662
		f 3 4152 -4151 4153
		mu 0 3 1673 1672 1671
		f 3 4154 -4154 4155
		mu 0 3 1674 1673 1671
		f 3 4156 -4155 4157
		mu 0 3 1675 1673 1674
		f 3 -4158 4158 4159
		mu 0 3 1675 1674 1676
		f 3 4160 4161 -4159
		mu 0 3 1674 1670 1676
		f 3 4162 -4162 4163
		mu 0 3 1677 1676 1670
		f 3 -4164 4164 4165
		mu 0 3 1677 1670 1623
		f 3 -4163 4166 4167
		mu 0 3 1676 1677 1622
		f 3 4168 -4168 4169
		mu 0 3 1678 1676 1622
		f 3 4170 -4169 4171
		mu 0 3 1679 1676 1678
		f 3 4172 -4172 4173
		mu 0 3 1615 1679 1678
		f 3 4174 4175 -4173
		mu 0 3 1615 1680 1679
		f 3 -4176 4176 4177
		mu 0 3 1679 1680 1660
		f 3 4178 -4178 4179
		mu 0 3 1672 1679 1660
		f 3 4180 -4179 4181
		mu 0 3 1675 1679 1672
		f 3 4182 4183 -4175
		mu 0 3 1615 1611 1680
		f 3 4184 -4184 4185
		mu 0 3 1658 1680 1611
		f 3 -4171 -4181 -4160
		mu 0 3 1676 1679 1675
		f 3 -4182 -4153 -4157
		mu 0 3 1675 1672 1673
		f 3 -4156 -4147 -4161
		mu 0 3 1674 1671 1670
		f 3 -4165 -4145 4186
		mu 0 3 1623 1670 1669
		f 3 -4187 4187 4188
		mu 0 3 1623 1669 1648
		f 3 -4135 4189 -4140
		mu 0 3 1666 1653 1668
		f 3 4190 -4131 -4138
		mu 0 3 1667 1663 1665
		f 3 -4129 4191 4192
		mu 0 3 1664 1661 1654
		f 3 -4150 -4128 -4191
		mu 0 3 1667 1662 1663
		f 3 -4180 -4126 -4152
		mu 0 3 1672 1660 1662
		f 3 -4177 -4185 -4121
		mu 0 3 1660 1680 1658
		f 3 4193 -4124 -4119
		mu 0 3 1656 1661 1659
		f 3 4194 -4118 4195
		mu 0 3 1681 1657 1658
		f 3 4196 -4196 4197
		mu 0 3 1608 1681 1658
		f 3 4198 4199 -4195
		mu 0 3 1681 1682 1657
		f 3 4200 -4200 4201
		mu 0 3 1376 1657 1682
		f 3 -4201 4202 4203
		mu 0 3 1657 1376 1683
		f 3 -4199 4204 4205
		mu 0 3 1682 1681 1684
		f 3 -4206 4206 4207
		mu 0 3 1682 1684 1378
		f 3 4208 4209 -4207
		mu 0 3 1684 1685 1378
		f 3 -4210 4210 4211
		mu 0 3 1378 1685 1382
		f 3 4212 4213 -4211
		mu 0 3 1685 1607 1382
		f 3 4214 -4213 -4209
		mu 0 3 1684 1607 1685
		f 3 4215 -4215 -4205
		mu 0 3 1681 1607 1684
		f 3 4216 -4116 -4204
		mu 0 3 1683 1655 1657
		f 3 4217 4218 -4217
		mu 0 3 1683 1686 1655
		f 3 4219 4220 -4218
		mu 0 3 1683 1350 1686
		f 3 4221 -4221 4222
		mu 0 3 1652 1686 1350
		f 3 -4220 4223 4224
		mu 0 3 1350 1683 1374
		f 3 -4194 -4113 -4192
		mu 0 3 1661 1656 1654
		f 3 -4112 -4219 -4222
		mu 0 3 1652 1655 1686
		f 3 -4133 -4193 -4109
		mu 0 3 1653 1664 1654
		f 3 -4190 -4107 4225
		mu 0 3 1668 1653 1650
		f 3 -4099 -4143 -4226
		mu 0 3 1650 1649 1668
		f 3 -4144 -4091 -4188
		mu 0 3 1669 1649 1648
		f 3 -4093 -4077 -4082
		mu 0 3 1646 1643 1644
		f 3 -4080 -4062 4226
		mu 0 3 1645 1641 1640
		f 3 -4086 -4227 -4060
		mu 0 3 1639 1645 1640
		f 3 4227 -4085 -4058
		mu 0 3 1631 1647 1639
		f 3 -4031 -4048 -4056
		mu 0 3 1630 1632 1637
		f 3 -4029 -4088 -4228
		mu 0 3 1631 1629 1647
		f 3 4228 -4027 -4055
		mu 0 3 1638 1628 1630
		f 3 -4025 4229 -4089
		mu 0 3 1629 1626 1648
		f 3 -4052 -4023 -4229
		mu 0 3 1638 1627 1628
		f 3 4230 -4022 -4054
		mu 0 3 357 1625 1627
		f 3 -4231 4231 4232
		mu 0 3 1625 357 1687
		f 3 -4232 4233 4234
		mu 0 3 1687 357 1085
		f 3 4235 4236 -4235
		mu 0 3 1085 1688 1687
		f 3 4237 4238 -4237
		mu 0 3 1688 1689 1687
		f 3 4239 -4238 4240
		mu 0 3 1690 1689 1688
		f 3 -4241 4241 4242
		mu 0 3 1690 1688 1087
		f 3 4243 -4240 4244
		mu 0 3 1620 1689 1690
		f 3 -4239 4245 -4233
		mu 0 3 1687 1689 1625
		f 3 -4230 -4019 -4189
		mu 0 3 1648 1626 1623
		f 3 -4246 4246 -4018
		mu 0 3 1625 1689 1624
		f 3 4247 -4015 -4247
		mu 0 3 1689 1621 1624
		f 3 -4166 -4013 -4167
		mu 0 3 1677 1623 1622
		f 3 4248 -4170 -4011
		mu 0 3 1618 1678 1622
		f 3 -4244 -4010 -4248
		mu 0 3 1689 1620 1621
		f 3 4249 -4007 -4245
		mu 0 3 1690 1619 1620
		f 3 4250 4251 -4250
		mu 0 3 1690 1088 1619
		f 3 -4252 4252 4253
		mu 0 3 1619 1088 1691
		f 3 -4254 4254 -4006
		mu 0 3 1619 1691 1617
		f 3 4255 4256 -4255
		mu 0 3 1691 1692 1617
		f 3 4257 -4257 4258
		mu 0 3 1693 1617 1692
		f 3 4259 4260 -4259
		mu 0 3 1692 1093 1693
		f 3 4261 -4261 4262
		mu 0 3 1119 1693 1093
		f 3 -4262 4263 4264
		mu 0 3 1693 1119 1613
		f 3 -4258 -4265 4265
		mu 0 3 1617 1693 1613
		f 3 -4256 4266 -4260
		mu 0 3 1692 1691 1093
		f 3 4267 -4249 -4003
		mu 0 3 1616 1678 1618
		f 3 -4174 -4268 -3999
		mu 0 3 1615 1678 1616
		f 3 -4002 -4266 -3995
		mu 0 3 1614 1617 1613
		f 3 -3994 -4264 4268
		mu 0 3 1610 1613 1119
		f 3 -4183 -3998 -3991
		mu 0 3 1611 1615 1612
		f 3 -4198 -4186 -3989
		mu 0 3 1608 1658 1611
		f 3 -3979 -4216 -4197
		mu 0 3 1608 1607 1681
		f 3 -3982 -3988 -3973
		mu 0 3 1606 1609 1592
		f 3 -3916 -3923 -3949
		mu 0 3 1588 1591 1594
		f 3 -3953 -3907 -3948
		mu 0 3 1601 1587 1588
		f 3 4269 -3911 -3903
		mu 0 3 1387 1590 1586
		f 3 -3899 -3906 4270
		mu 0 3 1558 1585 1587
		f 3 4271 -3816 -3795
		mu 0 3 1556 1565 1559
		f 3 -4271 -3954 -3794
		mu 0 3 1558 1587 1557
		f 3 -3956 4272 -3791
		mu 0 3 1557 1603 1554
		f 3 -3789 -3898 -4272
		mu 0 3 1556 1555 1565
		f 3 -3785 -4273 -3963
		mu 0 3 1552 1554 1603
		f 3 -3783 -3838 -3787
		mu 0 3 1553 1551 1555
		f 3 -3962 4273 -3782
		mu 0 3 1552 1605 1550
		f 3 -4274 4274 4275
		mu 0 3 1550 1605 1538
		f 3 -3839 -3779 -3840
		mu 0 3 1571 1551 1549
		f 3 -3777 4276 4277
		mu 0 3 1547 1550 1539
		f 3 -3896 -3841 -3775
		mu 0 3 1548 1570 1549
		f 3 -3895 -3773 -3892
		mu 0 3 1584 1548 1545
		f 3 4278 -3772 4279
		mu 0 3 1541 1546 1547
		f 3 -3870 -3893 -3767
		mu 0 3 1544 1582 1545
		f 3 -3866 -3765 -3876
		mu 0 3 1581 1544 1543
		f 3 -3759 -3769 -4279
		mu 0 3 1541 1542 1546
		f 3 -4278 -3757 -4280
		mu 0 3 1547 1539 1541
		f 3 -4277 -4276 -3753
		mu 0 3 1539 1550 1538
		f 3 -3964 -3751 -4275
		mu 0 3 1605 1537 1538
		f 3 -3967 -3937 -3749
		mu 0 3 1537 1598 1536
		f 3 -3756 -3745 4280
		mu 0 3 1540 1535 1533
		f 3 -4281 -3739 -3761
		mu 0 3 1540 1533 1532
		f 3 -3763 -3735 -3877
		mu 0 3 1543 1532 1531
		f 3 4281 -3727 4282
		mu 0 3 1694 1528 1529
		f 3 -4283 4283 4284
		mu 0 3 1694 1529 1195
		f 3 4285 -4282 4286
		mu 0 3 1695 1528 1694
		f 3 -4287 4287 4288
		mu 0 3 1695 1694 1204
		f 3 4289 -4289 4290
		mu 0 3 1209 1695 1204
		f 3 4291 -4290 4292
		mu 0 3 1521 1695 1209
		f 3 4293 -4293 4294
		mu 0 3 1510 1521 1209
		f 3 4295 4296 -4292
		mu 0 3 1521 1527 1695
		f 3 -4297 -3726 -4286
		mu 0 3 1695 1527 1528
		f 3 -3874 -3734 -3721
		mu 0 3 1525 1531 1526
		f 3 -3878 -3873 -3719
		mu 0 3 1523 1579 1525
		f 3 -3718 -3724 4297
		mu 0 3 1522 1524 1527
		f 3 -3886 -3879 -3715
		mu 0 3 1520 1578 1523
		f 3 -3714 -4298 -4296
		mu 0 3 1521 1522 1527
		f 3 -3712 -4294 4298
		mu 0 3 1519 1521 1510
		f 3 -3887 -3709 4299
		mu 0 3 1583 1520 1518
		f 3 -4300 -3705 -3885
		mu 0 3 1583 1518 1514
		f 3 -3708 4300 -3684
		mu 0 3 1512 1519 1511
		f 3 -4301 -4299 -3682
		mu 0 3 1511 1519 1510
		f 3 -3681 4301 -3659
		mu 0 3 1504 1510 1502
		f 3 -4302 4302 4303
		mu 0 3 1502 1510 1210
		f 3 -3655 -4304 4304
		mu 0 3 1214 1502 1210
		f 3 -3638 -3668 -3657
		mu 0 3 1499 1498 1503
		f 3 4305 4306 -3632
		mu 0 3 1497 1696 1471
		f 3 -3630 4307 -4306
		mu 0 3 1497 1496 1696
		f 3 4308 -4308 4309
		mu 0 3 1492 1696 1496
		f 3 -3650 -3626 -3641
		mu 0 3 1500 1494 1495
		f 3 -3622 -4310 -3629
		mu 0 3 1493 1492 1496
		f 3 -3620 4310 -4309
		mu 0 3 1492 1472 1696
		f 3 -3651 -3614 -3625
		mu 0 3 1494 1488 1490
		f 3 -3616 -3612 4311
		mu 0 3 1491 1489 1487
		f 3 -4312 -3606 4312
		mu 0 3 1491 1487 1485
		f 3 -3605 -3609 4313
		mu 0 3 1484 1486 1229
		f 3 -4313 -3602 -3618
		mu 0 3 1491 1485 1472
		f 3 -4314 4314 -3598
		mu 0 3 1484 1229 1483
		f 3 -3565 -3572 4315
		mu 0 3 1474 1475 1479
		f 3 -4316 4316 4317
		mu 0 3 1474 1479 1468
		f 3 4318 4319 -4317
		mu 0 3 1479 1697 1468
		f 3 4320 4321 -4320
		mu 0 3 1697 1698 1468
		f 3 4322 -4321 4323
		mu 0 3 1699 1698 1697
		f 3 -4324 4324 4325
		mu 0 3 1699 1697 1261
		f 3 -4326 4326 4327
		mu 0 3 1699 1261 1264
		f 3 4328 -4323 4329
		mu 0 3 1266 1698 1699
		f 3 4330 4331 -4319
		mu 0 3 1479 1260 1697
		f 3 -3560 -3600 -3566
		mu 0 3 1473 1472 1476
		f 3 -3558 -4307 -4311
		mu 0 3 1472 1471 1696
		f 3 -3563 4332 -3554
		mu 0 3 1470 1474 1469
		f 3 -4318 -3552 -4333
		mu 0 3 1474 1468 1469
		f 3 4333 -3550 -4322
		mu 0 3 1698 1467 1468
		f 3 4334 -4334 4335
		mu 0 3 1269 1467 1698
		f 3 4336 -3549 -4335
		mu 0 3 1269 1465 1467
		f 3 -3635 -3556 -3546
		mu 0 3 1464 1471 1466
		f 3 -3545 4337 4338
		mu 0 3 1462 1465 1270
		f 3 4339 -4339 4340
		mu 0 3 1700 1462 1270
		f 3 4341 -4341 4342
		mu 0 3 1701 1700 1270
		f 3 -4342 4343 4344
		mu 0 3 1700 1701 1273
		f 3 -3670 -3636 -3542
		mu 0 3 1463 1498 1464
		f 3 -3672 -3671 -3540
		mu 0 3 1461 1508 1463
		f 3 -3539 -4340 4345
		mu 0 3 1460 1462 1700
		f 3 4346 -3674 -3536
		mu 0 3 1459 1506 1461
		f 3 -4346 4347 -3535
		mu 0 3 1460 1700 1456
		f 3 4348 4349 -4348
		mu 0 3 1700 1276 1456
		f 3 -3676 -4347 -3532
		mu 0 3 1458 1506 1459
		f 3 -3686 -3678 -3530
		mu 0 3 1457 1509 1458
		f 3 -3700 -3688 -3528
		mu 0 3 1455 1513 1457
		f 3 -3527 -4350 4350
		mu 0 3 1454 1456 1276
		f 3 4351 -3701 -3524
		mu 0 3 1453 1516 1455
		f 3 -3698 -4352 -3518
		mu 0 3 1451 1516 1453
		f 3 -3514 -3704 -3699
		mu 0 3 1451 1450 1517
		f 3 -3884 -3703 -3510
		mu 0 3 1449 1514 1450
		f 3 -3856 -3883 -3508
		mu 0 3 1447 1577 1449
		f 3 -3507 4352 4353
		mu 0 3 1445 1448 1281
		f 3 4354 -4354 4355
		mu 0 3 1702 1445 1281
		f 3 -3857 -3504 -3847
		mu 0 3 1573 1447 1446
		f 3 -3846 -3502 4356
		mu 0 3 1569 1446 1443
		f 3 -3500 -4355 4357
		mu 0 3 1444 1445 1702
		f 3 4358 -4358 4359
		mu 0 3 1440 1444 1702
		f 3 4360 4361 -4360
		mu 0 3 1702 1284 1440
		f 3 -4357 -3496 -3831
		mu 0 3 1569 1443 1442
		f 3 -3494 4362 4363
		mu 0 3 1442 1439 1406
		f 3 -3492 -3499 -4359
		mu 0 3 1440 1441 1444
		f 3 -4363 -3486 4364
		mu 0 3 1406 1439 1437
		f 3 -3466 -3489 4365
		mu 0 3 1432 1434 1286
		f 3 -3470 -3465 -3458
		mu 0 3 1430 1433 1431
		f 3 -3456 4366 -3474
		mu 0 3 1430 1429 1420
		f 3 -3450 4367 4368
		mu 0 3 1427 1428 1288
		f 3 -3448 4369 4370
		mu 0 3 1425 1427 1703
		f 3 4371 -4371 4372
		mu 0 3 1302 1425 1703
		f 3 4373 -4372 4374
		mu 0 3 1305 1425 1302
		f 3 4375 4376 -4374
		mu 0 3 1305 1704 1425
		f 3 4377 4378 -4370
		mu 0 3 1427 1296 1703
		f 3 4379 -3444 -4377
		mu 0 3 1704 1424 1425
		f 3 4380 -4380 4381
		mu 0 3 1705 1424 1704
		f 3 4382 4383 -4382
		mu 0 3 1704 1313 1705
		f 3 4384 -4384 4385
		mu 0 3 1419 1705 1313
		f 3 -3442 -4381 4386
		mu 0 3 1421 1424 1705
		f 3 -3440 -3455 -3447
		mu 0 3 1423 1422 1426
		f 3 -4367 -3454 -3438
		mu 0 3 1420 1429 1422
		f 3 -4387 -4385 -3437
		mu 0 3 1421 1705 1419
		f 3 -3477 -3475 -3434
		mu 0 3 1418 1436 1420
		f 3 -3433 -4386 4387
		mu 0 3 1417 1419 1313
		f 3 -3476 -3430 -3480
		mu 0 3 1435 1418 1415
		f 3 4388 -3424 4389
		mu 0 3 1318 1414 1416
		f 3 -3482 -3422 4390
		mu 0 3 1438 1415 1413
		f 3 -3421 -4389 4391
		mu 0 3 1412 1414 1318
		f 3 -3485 -4391 -3418
		mu 0 3 1410 1438 1413
		f 3 4392 -3417 4393
		mu 0 3 1706 1411 1412
		f 3 4394 -4394 4395
		mu 0 3 1319 1706 1412
		f 3 -3414 -4393 4396
		mu 0 3 1409 1411 1706
		f 3 4397 -4397 4398
		mu 0 3 1707 1409 1706
		f 3 -4399 4399 4400
		mu 0 3 1707 1706 1357
		f 3 4401 -4401 4402
		mu 0 3 1361 1707 1357
		f 3 4403 4404 -4402
		mu 0 3 1361 1407 1707
		f 3 4405 -3484 -3412
		mu 0 3 1408 1437 1410
		f 3 -3411 -4398 -4405
		mu 0 3 1407 1409 1707
		f 3 -3408 -4365 -4406
		mu 0 3 1408 1406 1437
		f 3 -3828 -4364 -3402
		mu 0 3 1405 1442 1406
		f 3 -3829 -3400 4406
		mu 0 3 1567 1405 1403
		f 3 -3399 -3406 4407
		mu 0 3 1401 1404 1363
		f 3 -3823 -4407 -3396
		mu 0 3 1402 1567 1403
		f 3 -3819 -3394 4408
		mu 0 3 1564 1402 1400
		f 3 -3810 -4409 -3388
		mu 0 3 1399 1564 1400
		f 3 -3383 -3366 -3375
		mu 0 3 1398 1392 1395
		f 3 -3812 -3386 -3364
		mu 0 3 1393 1399 1394
		f 3 -3362 4409 -3811
		mu 0 3 1393 1391 1563
		f 3 4410 -3360 -3382
		mu 0 3 1380 1389 1392
		f 3 -3358 -3806 -4410
		mu 0 3 1391 1390 1563
		f 3 -3814 -3805 -3356
		mu 0 3 1388 1562 1390
		f 3 4411 -3354 -4411
		mu 0 3 1380 1386 1389
		f 3 -3352 -3901 -3813
		mu 0 3 1388 1387 1560
		f 3 -3350 -3913 -4270
		mu 0 3 1387 1385 1590
		f 3 -3346 -3975 -3914
		mu 0 3 1385 1384 1589
		f 3 -3978 -3344 4412
		mu 0 3 1607 1384 1383
		f 3 -4413 -3342 -4214
		mu 0 3 1607 1383 1382
		f 3 -3349 -4412 -3338
		mu 0 3 1381 1386 1380
		f 3 -4212 -3340 -3334
		mu 0 3 1378 1382 1379
		f 3 -4208 -3332 -4202
		mu 0 3 1682 1378 1376
		f 3 -3337 -3380 -3330
		mu 0 3 1377 1380 1375
		f 3 -3328 -4224 -4203
		mu 0 3 1376 1374 1683
		f 3 -3322 -3327 -3379
		mu 0 3 1372 1373 1375
		f 3 -3325 -3318 4413
		mu 0 3 1374 1371 1351
		f 3 -3321 -3384 -3313
		mu 0 3 1369 1372 1368
		f 3 -3373 -3308 -3385
		mu 0 3 1397 1365 1368
		f 3 -3372 -3391 -3300
		mu 0 3 1365 1396 1364
		f 3 -4408 -3298 -3393
		mu 0 3 1401 1363 1364
		f 3 -3296 -3407 -4404
		mu 0 3 1361 1363 1407
		f 3 -3302 -3294 -3306
		mu 0 3 1366 1362 1360
		f 3 -3307 -3290 -3310
		mu 0 3 1367 1360 1359
		f 3 -3315 -3288 4414
		mu 0 3 1370 1359 1354
		f 3 -3293 -4403 -3286
		mu 0 3 1358 1361 1357
		f 3 -4400 4415 -3284
		mu 0 3 1357 1706 1356
		f 3 -4416 4416 4417
		mu 0 3 1356 1706 1320
		f 3 4418 -4415 -3272
		mu 0 3 1352 1370 1354
		f 3 4419 -3269 4420
		mu 0 3 1340 1348 1336
		f 3 4421 4422 -4420
		mu 0 3 1340 1343 1348
		f 3 -3317 -4419 -3266
		mu 0 3 1351 1370 1352
		f 3 -3264 -4225 -4414
		mu 0 3 1351 1350 1374
		f 3 -4105 -4223 -3262
		mu 0 3 1349 1652 1350
		f 3 -3260 -4102 -4106
		mu 0 3 1349 1347 1651
		f 3 -3259 -4423 -3255
		mu 0 3 1346 1348 1343
		f 3 -3252 -4098 -3256
		mu 0 3 1345 1344 1347
		f 3 -4096 -3250 -4075
		mu 0 3 1643 1344 1342
		f 3 -3244 -3249 -4422
		mu 0 3 1340 1341 1343
		f 3 -4073 -3246 -3240
		mu 0 3 1338 1342 1339
		f 3 -3243 -4421 -3236
		mu 0 3 1337 1340 1336
		f 3 -3271 4423 -3232
		mu 0 3 1336 1353 1334
		f 3 -3228 -4424 -3275
		mu 0 3 1333 1334 1353
		f 3 -3283 -3226 -3276
		mu 0 3 1355 1332 1333
		f 3 4424 4425 -3224
		mu 0 3 1332 1323 1329
		f 3 -3231 -3222 4426
		mu 0 3 1335 1331 1330
		f 3 4427 -4427 4428
		mu 0 3 375 1335 1330
		f 3 -4429 4429 4430
		mu 0 3 375 1330 1708
		f 3 4431 4432 -4430
		mu 0 3 1330 1709 1708
		f 3 -4433 4433 4434
		mu 0 3 1708 1709 379
		f 3 -4434 4435 4436
		mu 0 3 379 1709 1710
		f 3 -4436 4437 4438
		mu 0 3 1710 1709 1711
		f 3 4439 4440 -4439
		mu 0 3 1711 383 1710
		f 3 -4438 4441 4442
		mu 0 3 1711 1709 1326
		f 3 -4443 4443 4444
		mu 0 3 1711 1326 400
		f 3 4445 -4442 -4432
		mu 0 3 1330 1326 1709
		f 3 4446 -3218 -4426
		mu 0 3 1323 1328 1329
		f 3 -3221 -3214 -4446
		mu 0 3 1330 1327 1326
		f 3 -3212 4447 4448
		mu 0 3 1326 1325 1712
		f 3 4449 -4449 4450
		mu 0 3 1713 1326 1712
		f 3 -4451 4451 4452
		mu 0 3 1713 1712 1714
		f 3 4453 4454 -4452
		mu 0 3 1712 1308 1714
		f 3 -4454 4455 4456
		mu 0 3 1308 1712 1311
		f 3 4457 4458 -4453
		mu 0 3 1714 404 1713
		f 3 4459 4460 -4458
		mu 0 3 1714 407 404
		f 3 4461 4462 -4460
		mu 0 3 1714 1307 407
		f 3 -4450 4463 4464
		mu 0 3 1326 1713 403
		f 3 4465 -4456 -4448
		mu 0 3 1325 1311 1712
		f 3 -3210 4466 -4466
		mu 0 3 1325 1314 1311
		f 3 -3206 -3216 -4447
		mu 0 3 1323 1324 1328
		f 3 -4425 -3282 -3204
		mu 0 3 1323 1332 1322
		f 3 -3280 -4418 -3203
		mu 0 3 1322 1356 1320
		f 3 -4417 -4395 -3198
		mu 0 3 1320 1706 1319
		f 3 -4396 -4392 -3196
		mu 0 3 1319 1412 1318
		f 3 -3429 -3194 -4390
		mu 0 3 1416 1316 1318
		f 3 -3201 -3192 4467
		mu 0 3 1321 1317 1315
		f 3 -3428 -4388 -3190
		mu 0 3 1316 1417 1313
		f 3 -4468 -3188 -3208
		mu 0 3 1321 1315 1314
		f 3 -4383 4468 -3184
		mu 0 3 1313 1704 1310
		f 3 -3187 -3182 -4467
		mu 0 3 1314 1312 1311
		f 3 4469 -3178 -4469
		mu 0 3 1704 1306 1310
		f 3 -4457 -3180 -3176
		mu 0 3 1308 1311 1309
		f 3 -3174 -4462 -4455
		mu 0 3 1308 1307 1714
		f 3 -4470 -4376 -3170
		mu 0 3 1306 1704 1305
		f 3 -3167 -4375 -3162
		mu 0 3 1303 1305 1302
		f 3 4470 -3161 -4373
		mu 0 3 1703 1297 1302
		f 3 -3158 4471 -3164
		mu 0 3 1301 411 1304
		f 3 -4471 -4379 -3139
		mu 0 3 1297 1703 1296
		f 3 4472 -3137 -4378
		mu 0 3 1427 1291 1296
		f 3 -3144 -3135 -3149
		mu 0 3 1299 1295 1294
		f 3 -4473 -4369 -3124
		mu 0 3 1291 1427 1288
		f 3 -3121 4473 -3125
		mu 0 3 1290 1289 1292
		f 3 4474 -4474 4475
		mu 0 3 1715 1292 1289
		f 3 -4475 4476 4477
		mu 0 3 1292 1715 1274
		f 3 4478 -4477 4479
		mu 0 3 1716 1274 1715;
	setAttr ".fc[2500:2999]"
		f 3 4480 -4480 4481
		mu 0 3 1283 1716 1715
		f 3 4482 -4479 4483
		mu 0 3 1278 1274 1716
		f 3 4484 -4476 -3119
		mu 0 3 1285 1715 1289
		f 3 -3463 -3117 -4368
		mu 0 3 1428 1287 1288
		f 3 -3115 -3462 -4366
		mu 0 3 1286 1287 1432
		f 3 -4362 -3113 -3491
		mu 0 3 1440 1284 1286
		f 3 -3111 -4482 -4485
		mu 0 3 1285 1283 1715
		f 3 -4361 4485 -3109
		mu 0 3 1284 1702 1282
		f 3 -4484 -4481 -3107
		mu 0 3 1278 1716 1283
		f 3 -4486 -4356 -3105
		mu 0 3 1282 1702 1281
		f 3 -4353 -3512 -3103
		mu 0 3 1281 1448 1280
		f 3 -3517 4486 -3101
		mu 0 3 1280 1452 1279
		f 3 -4487 -3523 -3099
		mu 0 3 1279 1452 1277
		f 3 -3522 -4351 -3095
		mu 0 3 1277 1454 1276
		f 3 -3094 -4349 -4345
		mu 0 3 1273 1276 1700
		f 3 -4483 -3097 -3091
		mu 0 3 1274 1278 1275
		f 3 -3089 -3130 -4478
		mu 0 3 1274 1272 1292
		f 3 -4344 4487 -3087
		mu 0 3 1273 1701 1271
		f 3 -3129 -3085 4488
		mu 0 3 1293 1272 1268
		f 3 -4343 -3083 -4488
		mu 0 3 1701 1270 1271
		f 3 -4337 -3081 -4338
		mu 0 3 1465 1269 1270
		f 3 -3079 -4336 -4329
		mu 0 3 1266 1269 1698
		f 3 -3132 -4489 -3077
		mu 0 3 1267 1293 1268
		f 3 -3150 -3134 -3075
		mu 0 3 1265 1294 1267
		f 3 -4330 -4328 -3073
		mu 0 3 1266 1699 1264
		f 3 -3068 -4327 -3061
		mu 0 3 1262 1264 1261
		f 3 -3060 -4325 -4332
		mu 0 3 1260 1261 1697
		f 3 -3057 -4331 -3575
		mu 0 3 1257 1260 1479
		f 3 -3579 -3049 -3574
		mu 0 3 1478 1256 1257
		f 3 4489 -3052 -3045
		mu 0 3 1254 1258 1255
		f 3 -4490 4490 4491
		mu 0 3 1258 1254 429
		f 3 -4491 -3043 4492
		mu 0 3 429 1254 1253
		f 3 -3578 -3039 -3048
		mu 0 3 1256 1251 1252
		f 3 -3035 4493 -3042
		mu 0 3 1250 431 1253
		f 3 -3029 -3025 4494
		mu 0 3 1249 1247 1242
		f 3 -4495 4495 4496
		mu 0 3 1249 1242 1717
		f 3 4497 4498 -4497
		mu 0 3 1717 1718 1249
		f 3 -4499 4499 4500
		mu 0 3 1249 1718 434
		f 3 -4500 4501 4502
		mu 0 3 434 1718 1719
		f 3 -4502 4503 4504
		mu 0 3 1719 1718 1241
		f 3 4505 4506 -4505
		mu 0 3 1241 1720 1719
		f 3 -4507 4507 4508
		mu 0 3 1719 1720 440
		f 3 4509 -4506 4510
		mu 0 3 518 1720 1241
		f 3 4511 -4510 4512
		mu 0 3 1721 1720 518
		f 3 4513 -4512 4514
		mu 0 3 442 1720 1721
		f 3 -4498 4515 -4504
		mu 0 3 1718 1717 1241
		f 3 -3023 -3037 -3581
		mu 0 3 1245 1246 1251
		f 3 -3021 -3585 4516
		mu 0 3 1244 1245 1481
		f 3 -3019 -4517 -3588
		mu 0 3 1243 1244 1481
		f 3 -3017 -3591 4517
		mu 0 3 1240 1243 1234
		f 3 -4496 -3015 -4516
		mu 0 3 1717 1242 1241
		f 3 -3013 4518 4519
		mu 0 3 1241 1239 519
		f 3 -3006 -3011 -4518
		mu 0 3 1234 1238 1240
		f 3 -3590 4520 -2989
		mu 0 3 1234 1482 1232
		f 3 -4521 -3593 -2985
		mu 0 3 1232 1482 1231
		f 3 -3595 4521 -2983
		mu 0 3 1231 1483 1230
		f 3 -4315 -2981 -4522
		mu 0 3 1483 1229 1230
		f 3 4522 -2979 -3610
		mu 0 3 1488 1226 1229
		f 3 -2977 -2995 -2988
		mu 0 3 1228 1227 1233
		f 3 -3648 -2974 -4523
		mu 0 3 1488 1225 1226
		f 3 4523 -2971 -3646
		mu 0 3 1501 1223 1225
		f 3 -2969 -2997 -2975
		mu 0 3 1224 1222 1227
		f 3 -2967 -4524 4524
		mu 0 3 1220 1223 1501
		f 3 -3001 -2965 4525
		mu 0 3 1237 1222 1221
		f 3 4526 -4526 4527
		mu 0 3 529 1237 1221
		f 3 -2961 -4525 -3645
		mu 0 3 1219 1220 1501
		f 3 4528 -2951 -2957
		mu 0 3 1219 1215 1217
		f 3 -3652 -2947 -4529
		mu 0 3 1219 1214 1215
		f 3 -2943 4529 -2950
		mu 0 3 1213 1212 1216
		f 3 4530 4531 -4530
		mu 0 3 1212 1207 1216
		f 3 -4532 4532 4533
		mu 0 3 1216 1207 562
		f 3 -2940 -2946 -4305
		mu 0 3 1210 1211 1214
		f 3 -4295 -2937 -4303
		mu 0 3 1510 1209 1210
		f 3 -2933 -4531 -2941
		mu 0 3 1208 1207 1212
		f 3 -2931 4534 4535
		mu 0 3 1207 1206 563
		f 3 -2929 4536 4537
		mu 0 3 1206 1203 565
		f 3 -4291 -2927 -2935
		mu 0 3 1209 1204 1205
		f 3 -4288 4538 -2925
		mu 0 3 1204 1694 1201
		f 3 4539 4540 -4539
		mu 0 3 1694 1197 1201
		f 3 -2923 4541 -4537
		mu 0 3 1203 1202 565
		f 3 4542 4543 -4542
		mu 0 3 1202 1722 565
		f 3 4544 -4543 -2921
		mu 0 3 1200 1722 1202
		f 3 4545 4546 -4545
		mu 0 3 1200 1723 1722
		f 3 4547 4548 -4547
		mu 0 3 1723 1724 1722
		f 3 -4549 4549 4550
		mu 0 3 1722 1724 566
		f 3 4551 4552 -4550
		mu 0 3 1724 1725 566
		f 3 4553 4554 -4552
		mu 0 3 1724 1170 1725
		f 3 4555 -4555 4556
		mu 0 3 579 1725 1170
		f 3 4557 -4548 4558
		mu 0 3 1171 1724 1723
		f 3 4559 4560 -4559
		mu 0 3 1723 1199 1171
		f 3 -4560 -4546 -2917
		mu 0 3 1199 1723 1200
		f 3 4561 4562 -2915
		mu 0 3 1196 1726 1199
		f 3 4563 4564 -4563
		mu 0 3 1726 1173 1199
		f 3 4565 4566 -4564
		mu 0 3 1726 1176 1173
		f 3 -4566 4567 4568
		mu 0 3 1176 1726 1727
		f 3 -4569 4569 4570
		mu 0 3 1176 1727 1193
		f 3 4571 -4570 4572
		mu 0 3 1196 1193 1727
		f 3 -4568 -4562 -4573
		mu 0 3 1727 1726 1196
		f 3 -2914 -2919 -4541
		mu 0 3 1197 1198 1201
		f 3 -4540 -4285 -2911
		mu 0 3 1197 1694 1195
		f 3 -4284 -3732 -2907
		mu 0 3 1195 1529 1192
		f 3 -2909 -2905 -4572
		mu 0 3 1196 1194 1193
		f 3 -2899 -3731 -3738
		mu 0 3 1191 1192 1530
		f 3 4573 -2898 -3742
		mu 0 3 1534 1189 1191
		f 3 -3744 -2891 -4574
		mu 0 3 1534 1188 1189
		f 3 -3747 -3936 -2890
		mu 0 3 1188 1536 1187
		f 3 4574 4575 -2888
		mu 0 3 1187 1141 1185
		f 3 4576 4577 -2883
		mu 0 3 1185 1144 1184
		f 3 -2886 -2875 -2893
		mu 0 3 1186 1183 1181
		f 3 -2869 -2903 -2896
		mu 0 3 1181 1178 1190
		f 3 -2868 -2872 4578
		mu 0 3 1179 1180 1158
		f 3 4579 -2904 -2863
		mu 0 3 1177 1193 1178
		f 3 -4571 -4580 -2861
		mu 0 3 1176 1193 1177
		f 3 -2857 -2866 4580
		mu 0 3 1162 1175 1179
		f 3 -2859 -2851 -4567
		mu 0 3 1176 1174 1173
		f 3 -4565 -2849 -4561
		mu 0 3 1199 1173 1171
		f 3 -4558 -2845 -4554
		mu 0 3 1724 1171 1170
		f 3 -2855 -2829 -2848
		mu 0 3 1172 1165 1166
		f 3 4581 -2837 -2825
		mu 0 3 589 1169 1164
		f 3 -2822 -2827 -2856
		mu 0 3 1162 1163 1165
		f 3 -2818 -4581 4582
		mu 0 3 1160 1162 1179
		f 3 4583 4584 -2815
		mu 0 3 1159 1728 1161
		f 3 4585 -4585 4586
		mu 0 3 594 1161 1728
		f 3 4587 -4584 4588
		mu 0 3 1155 1728 1159
		f 3 4589 4590 -4588
		mu 0 3 1155 1729 1728
		f 3 4591 -4591 4592
		mu 0 3 1730 1728 1729
		f 3 4593 4594 -4593
		mu 0 3 1729 615 1730
		f 3 4595 4596 -4594
		mu 0 3 1729 1154 615
		f 3 4597 4598 -4592
		mu 0 3 1730 1731 1728
		f 3 4599 -4599 4600
		mu 0 3 596 1728 1731
		f 3 -4598 4601 4602
		mu 0 3 1731 1730 1732
		f 3 4603 -4603 4604
		mu 0 3 1733 1731 1732
		f 3 4605 -4605 4606
		mu 0 3 599 1733 1732
		f 3 4607 -4604 4608
		mu 0 3 598 1731 1733
		f 3 4609 4610 -4602
		mu 0 3 1730 610 1732
		f 3 -2813 -4583 -4579
		mu 0 3 1158 1160 1179
		f 3 -2809 -2874 -2878
		mu 0 3 1157 1158 1182
		f 3 -4589 -2811 -2805
		mu 0 3 1155 1159 1156
		f 3 -4590 -2803 -4596
		mu 0 3 1729 1155 1154
		f 3 -2788 4611 -2795
		mu 0 3 1150 1149 1152
		f 3 4612 4613 -4612
		mu 0 3 1149 1734 1152
		f 3 4614 4615 -4614
		mu 0 3 1734 1735 1152
		f 3 4616 4617 -4616
		mu 0 3 1735 627 1152
		f 3 -4615 4618 4619
		mu 0 3 1735 1734 1736
		f 3 4620 -4619 4621
		mu 0 3 1135 1736 1734
		f 3 4622 4623 -4620
		mu 0 3 1736 637 1735
		f 3 4624 4625 -4623
		mu 0 3 1736 1737 637
		f 3 4626 4627 -4626
		mu 0 3 1737 642 637
		f 3 -4625 4628 4629
		mu 0 3 1737 1736 1134
		f 3 4630 -4613 4631
		mu 0 3 1145 1734 1149
		f 3 4632 -4631 4633
		mu 0 3 1136 1734 1145
		f 3 -2785 -2808 -2880
		mu 0 3 1147 1148 1157
		f 3 -2882 -4578 -2782
		mu 0 3 1147 1184 1144
		f 3 -2786 -2780 -4632
		mu 0 3 1149 1146 1145
		f 3 -2778 4634 -4634
		mu 0 3 1145 1143 1136
		f 3 4635 -2777 -4577
		mu 0 3 1185 1142 1144
		f 3 -4636 -4576 -2773
		mu 0 3 1142 1185 1141
		f 3 -3933 -2770 -4575
		mu 0 3 1187 1140 1141
		f 3 -2769 -3932 4636
		mu 0 3 1139 1140 1595
		f 3 4637 -4637 4638
		mu 0 3 1131 1139 1595
		f 3 4639 -2766 -4638
		mu 0 3 1131 1137 1139
		f 3 -2764 -4635 -2774
		mu 0 3 1138 1136 1143
		f 3 -4622 -4633 -2760
		mu 0 3 1135 1734 1136
		f 3 -4621 -2758 -4629
		mu 0 3 1736 1135 1134
		f 3 4640 -4630 -2756
		mu 0 3 1128 1737 1134
		f 3 4641 -4641 4642
		mu 0 3 643 1737 1128
		f 3 -2752 -2762 -4640
		mu 0 3 1131 1133 1137
		f 3 -2749 -4639 -3925
		mu 0 3 1130 1131 1595
		f 3 4643 -2746 -3921
		mu 0 3 1593 1127 1130
		f 3 -2755 -2750 -2744
		mu 0 3 1128 1132 1129
		f 3 -4643 -2742 4644
		mu 0 3 643 1128 1125
		f 3 -4644 -3972 -2741
		mu 0 3 1127 1593 1126
		f 3 -3971 -2732 -2738
		mu 0 3 1126 1123 1124
		f 3 -3987 -2730 -3969
		mu 0 3 1592 1122 1123
		f 3 -3985 4645 -2728
		mu 0 3 1122 1610 1120
		f 3 -4646 -4269 -2722
		mu 0 3 1120 1610 1119
		f 3 -4263 -2633 -2720
		mu 0 3 1119 1093 1094
		f 3 -4267 4646 -2630
		mu 0 3 1093 1691 1089
		f 3 -2628 -2712 -2634
		mu 0 3 1092 1091 1095
		f 3 4647 -2713 -2626
		mu 0 3 1090 967 1091
		f 3 -4647 -4253 -2622
		mu 0 3 1089 1691 1088
		f 3 -4251 -4243 -2618
		mu 0 3 1088 1690 1087
		f 3 -4236 -2614 -4242
		mu 0 3 1688 1085 1087
		f 3 -2611 -4234 4648
		mu 0 3 982 1085 357
		f 3 -2301 4649 -2260
		mu 0 3 981 997 978
		f 3 -2612 -2257 -2616
		mu 0 3 1086 980 979
		f 3 -4650 -2311 -2253
		mu 0 3 978 997 976
		f 3 -2251 -2621 -2256
		mu 0 3 977 975 979
		f 3 -2249 -2312 -2314
		mu 0 3 974 976 1001
		f 3 -2247 4650 -2624
		mu 0 3 975 970 1090
		f 3 -2605 -2245 -2316
		mu 0 3 1002 973 974
		f 3 -2481 -2243 -2477
		mu 0 3 1055 972 973
		f 3 -2480 -2487 -2241
		mu 0 3 972 1056 971
		f 3 -2489 4651 -2239
		mu 0 3 971 963 968
		f 3 -2237 4652 -4651
		mu 0 3 970 969 1090
		f 3 -4653 -2235 -4648
		mu 0 3 1090 969 967
		f 3 -2231 -2705 -2710
		mu 0 3 967 966 1117
		f 3 -2229 -2691 -2689
		mu 0 3 966 964 1114
		f 3 -2233 -4652 -2227
		mu 0 3 965 968 963
		f 3 4653 -2692 -2225
		mu 0 3 961 1113 964
		f 3 -2495 -2223 -2488
		mu 0 3 1058 962 963
		f 3 -2499 -2221 -2494
		mu 0 3 1060 960 962
		f 3 -2219 4654 -4654
		mu 0 3 961 958 1113
		f 3 4655 -2218 -2498
		mu 0 3 951 959 960
		f 3 -4655 -2213 -2682
		mu 0 3 1113 958 957
		f 3 -2695 -2211 -2701
		mu 0 3 1116 957 956
		f 3 4656 -2209 4657
		mu 0 3 944 956 954
		f 3 -2215 4658 -2207
		mu 0 3 955 959 953
		f 3 -2201 -4659 4659
		mu 0 3 952 953 959
		f 3 -4660 -4656 -2199
		mu 0 3 952 959 951
		f 3 -2539 -2197 -2500
		mu 0 3 1061 950 951
		f 3 -2191 -2195 -2538
		mu 0 3 947 948 950
		f 3 -2194 -2187 -2203
		mu 0 3 949 946 945
		f 3 -2205 -2185 -4658
		mu 0 3 954 945 944
		f 3 -2183 -2702 -4657
		mu 0 3 944 940 956
		f 3 -2540 -2182 -2190
		mu 0 3 947 942 943
		f 3 -2547 -2179 -2541
		mu 0 3 1074 941 942
		f 3 4660 -2167 -2177
		mu 0 3 941 937 938
		f 3 -2548 -2165 -4661
		mu 0 3 941 935 937
		f 3 -2163 4661 -2171
		mu 0 3 936 934 939
		f 3 4662 4663 -4662
		mu 0 3 934 669 939
		f 3 -2162 -2549 4664
		mu 0 3 931 935 1076
		f 3 -2155 4665 4666
		mu 0 3 933 932 675
		f 3 -4667 4667 4668
		mu 0 3 933 675 672
		f 3 -2153 4669 4670
		mu 0 3 932 923 1738
		f 3 4671 4672 -4671
		mu 0 3 1738 676 932
		f 3 4673 4674 -4672
		mu 0 3 1738 1739 676
		f 3 -4675 4675 4676
		mu 0 3 676 1739 1740
		f 3 4677 4678 -4676
		mu 0 3 1739 1741 1740
		f 3 -4679 4679 4680
		mu 0 3 1740 1741 1742
		f 3 4681 4682 -4680
		mu 0 3 1741 1743 1742
		f 3 4683 4684 -4683
		mu 0 3 1743 1744 1742
		f 3 -4685 4685 4686
		mu 0 3 1742 1744 1745
		f 3 4687 4688 -4686
		mu 0 3 1744 1746 1745
		f 3 -4689 4689 4690
		mu 0 3 1745 1746 688
		f 3 -4691 4691 4692
		mu 0 3 1745 688 1747
		f 3 -4693 4693 4694
		mu 0 3 1745 1747 1748
		f 3 4695 -4694 4696
		mu 0 3 1749 1748 1747
		f 3 -4697 4697 4698
		mu 0 3 1749 1747 1750
		f 3 4699 -4699 4700
		mu 0 3 680 1749 1750
		f 3 4701 -4700 4702
		mu 0 3 1751 1749 680
		f 3 4703 -4703 4704
		mu 0 3 1752 1751 680
		f 3 4705 -4704 4706
		mu 0 3 677 1751 1752
		f 3 4707 4708 -4706
		mu 0 3 677 1740 1751
		f 3 -4709 4709 4710
		mu 0 3 1751 1740 1748
		f 3 4711 4712 -4698
		mu 0 3 1747 684 1750
		f 3 -4711 -4696 -4702
		mu 0 3 1751 1748 1749
		f 3 4713 4714 -4688
		mu 0 3 1744 895 1746
		f 3 -4715 4715 4716
		mu 0 3 1746 895 689
		f 3 -4687 -4695 4717
		mu 0 3 1742 1745 1748
		f 3 4718 4719 -4684
		mu 0 3 1743 1753 1744
		f 3 4720 4721 -4720
		mu 0 3 1753 896 1744
		f 3 4722 4723 -4719
		mu 0 3 1743 920 1753
		f 3 4724 -4724 4725
		mu 0 3 1754 1753 920
		f 3 4726 4727 -4725
		mu 0 3 1754 898 1753
		f 3 4728 4729 -4727
		mu 0 3 1754 919 898
		f 3 4730 4731 -4730
		mu 0 3 919 1755 898
		f 3 4732 4733 -4731
		mu 0 3 919 1756 1755
		f 3 4734 4735 -4734
		mu 0 3 1756 1757 1755
		f 3 4736 -4736 4737
		mu 0 3 903 1755 1757
		f 3 -4735 4738 4739
		mu 0 3 1757 1756 1758
		f 3 4740 4741 -4740
		mu 0 3 1758 905 1757
		f 3 -4739 4742 4743
		mu 0 3 1758 1756 915
		f 3 -4723 -4682 4744
		mu 0 3 920 1743 1741
		f 3 -4710 -4681 -4718
		mu 0 3 1748 1740 1742
		f 3 4745 4746 -4678
		mu 0 3 1739 922 1741
		f 3 4747 -4746 -4674
		mu 0 3 1738 922 1739
		f 3 -4665 -2557 -2150
		mu 0 3 931 1076 930
		f 3 4748 -2148 -2556
		mu 0 3 1077 929 930
		f 3 4749 4750 -4749
		mu 0 3 1077 1759 929
		f 3 -4750 4751 4752
		mu 0 3 1759 1077 248
		f 3 4753 -2145 -4751
		mu 0 3 1759 928 929
		f 3 4754 -4754 4755
		mu 0 3 1760 928 1759
		f 3 4756 4757 -4756
		mu 0 3 1759 1761 1760
		f 3 -4758 4758 4759
		mu 0 3 1760 1761 913
		f 3 4760 4761 -4760
		mu 0 3 913 1762 1760
		f 3 -4757 4762 4763
		mu 0 3 1761 1759 247
		f 3 -4762 4764 -4755
		mu 0 3 1760 1762 928
		f 3 4765 -2143 -4765
		mu 0 3 1762 926 928
		f 3 4766 4767 -4766
		mu 0 3 1762 914 926
		f 3 -2140 -4768 4768
		mu 0 3 925 926 914
		f 3 -2142 -2133 -2151
		mu 0 3 927 924 923
		f 3 -2131 -4748 -4670
		mu 0 3 923 922 1738
		f 3 -2129 -4745 -4747
		mu 0 3 922 920 1741
		f 3 -4726 -2125 -4729
		mu 0 3 1754 920 919
		f 3 4769 -4733 -2123
		mu 0 3 918 1756 919
		f 3 -4743 -4770 -2121
		mu 0 3 915 1756 918
		f 3 -2138 -2120 -2127
		mu 0 3 921 916 917
		f 3 -4769 -2117 -2137
		mu 0 3 925 914 916
		f 3 -2115 4770 -4744
		mu 0 3 915 911 1758
		f 3 -4767 -4761 -2113
		mu 0 3 914 1762 913
		f 3 -2111 -4759 4771
		mu 0 3 912 913 1761
		f 3 4772 -4772 4773
		mu 0 3 1763 912 1761
		f 3 -4774 4774 4775
		mu 0 3 1763 1761 245
		f 3 -4776 4776 4777
		mu 0 3 1763 245 240
		f 3 -4778 4778 4779
		mu 0 3 1763 240 237
		f 3 4780 -4780 4781
		mu 0 3 909 1763 237
		f 3 4782 -2110 -4773
		mu 0 3 1763 910 912
		f 3 4783 -4771 -2107
		mu 0 3 908 1758 911
		f 3 -2106 -4783 -4781
		mu 0 3 909 910 1763
		f 3 -4741 -4784 -2099
		mu 0 3 905 1758 908
		f 3 -4738 -4742 -2087
		mu 0 3 903 1757 905
		f 3 4784 -2086 -2094
		mu 0 3 193 902 904
		f 3 4785 -4737 -2083
		mu 0 3 900 1755 903
		f 3 -2073 4786 4787
		mu 0 3 899 901 869
		f 3 -4732 -4786 -2071
		mu 0 3 898 1755 900
		f 3 4788 -2069 -4788
		mu 0 3 869 897 899
		f 3 -4728 -2067 -4721
		mu 0 3 1753 898 896
		f 3 -2063 -4714 -4722
		mu 0 3 896 895 1744
		f 3 4789 -1973 -1967
		mu 0 3 868 873 871
		f 3 -4789 -1965 -2066
		mu 0 3 897 869 870
		f 3 -4787 -2080 -1963
		mu 0 3 869 901 867
		f 3 -2057 -4790 -1961
		mu 0 3 866 873 868
		f 3 -2058 -1957 4790
		mu 0 3 875 866 863
		f 3 -1955 -1960 -2082
		mu 0 3 864 865 867
		f 3 4791 -1953 4792
		mu 0 3 190 860 864
		f 3 -4791 -1951 -2055
		mu 0 3 875 863 862
		f 3 -2049 -2053 -1949
		mu 0 3 861 894 862
		f 3 -2051 -1948 -1939
		mu 0 3 857 861 858
		f 3 -2052 -1937 -2034
		mu 0 3 892 857 856
		f 3 -1942 4793 -1931
		mu 0 3 855 859 853
		f 3 -4794 4794 -1927
		mu 0 3 853 859 852
		f 3 4795 -4795 4796
		mu 0 3 1764 852 859
		f 3 4797 4798 -4797
		mu 0 3 859 187 1764
		f 3 4799 -4799 4800
		mu 0 3 1765 1764 187
		f 3 -4801 4801 4802
		mu 0 3 1765 187 181
		f 3 4803 -4803 4804
		mu 0 3 1766 1765 181
		f 3 4805 -4805 4806
		mu 0 3 177 1766 181
		f 3 4807 -4806 4808
		mu 0 3 1767 1766 177
		f 3 4809 4810 -4808
		mu 0 3 1767 851 1766
		f 3 4811 4812 -4811
		mu 0 3 851 1764 1766
		f 3 -4800 -4804 -4813
		mu 0 3 1764 1765 1766
		f 3 -1926 -4796 -4812
		mu 0 3 851 852 1764
		f 3 -1924 -4810 4813
		mu 0 3 850 851 1767
		f 3 4814 -4814 4815
		mu 0 3 1768 850 1767
		f 3 -4816 4816 4817
		mu 0 3 1768 1767 1769
		f 3 4818 -4818 4819
		mu 0 3 1770 1768 1769
		f 3 -4820 4820 4821
		mu 0 3 1770 1769 1771
		f 3 -4821 4822 4823
		mu 0 3 1771 1769 172
		f 3 -4823 4824 4825
		mu 0 3 172 1769 176
		f 3 4826 -4822 4827
		mu 0 3 1772 1770 1771
		f 3 4828 4829 -4828
		mu 0 3 1771 171 1772
		f 3 4830 4831 -4830
		mu 0 3 171 1773 1772
		f 3 4832 -4832 4833
		mu 0 3 1774 1772 1773
		f 3 -4834 4834 4835
		mu 0 3 1774 1773 1775
		f 3 4836 4837 -4836
		mu 0 3 1775 1776 1774
		f 3 4838 4839 -4837
		mu 0 3 1775 1777 1776
		f 3 4840 4841 -4840
		mu 0 3 1777 1778 1776
		f 3 4842 4843 -4842
		mu 0 3 1778 1779 1776
		f 3 4844 4845 -4844
		mu 0 3 1779 1772 1776
		f 3 4846 4847 -4845
		mu 0 3 1779 1780 1772
		f 3 4848 4849 -4847
		mu 0 3 1779 1781 1780
		f 3 4850 4851 -4850
		mu 0 3 1781 1782 1780
		f 3 -4852 4852 4853
		mu 0 3 1780 1782 1770
		f 3 4854 -4853 4855
		mu 0 3 1783 1770 1782
		f 3 4856 4857 -4856
		mu 0 3 1782 1784 1783
		f 3 4858 -4858 4859
		mu 0 3 1785 1783 1784
		f 3 4860 -4860 4861
		mu 0 3 1786 1785 1784
		f 3 4862 -4862 4863
		mu 0 3 1787 1786 1784
		f 3 4864 -4863 4865
		mu 0 3 1788 1786 1787
		f 3 -4866 4866 4867
		mu 0 3 1788 1787 1781
		f 3 -4868 4868 4869
		mu 0 3 1788 1781 1789
		f 3 4870 -4870 4871
		mu 0 3 1790 1788 1789
		f 3 4872 -4872 4873
		mu 0 3 1791 1790 1789
		f 3 -4874 4874 4875
		mu 0 3 1791 1789 1778
		f 3 4876 -4873 4877
		mu 0 3 1792 1790 1791
		f 3 4878 -4878 4879
		mu 0 3 1793 1792 1791
		f 3 -4880 4880 4881
		mu 0 3 1793 1791 1794
		f 3 4882 -4881 4883
		mu 0 3 1795 1794 1791
		f 3 4884 -4884 4885
		mu 0 3 1796 1795 1791
		f 3 -4886 4886 4887
		mu 0 3 1796 1791 1777
		f 3 4888 -4888 4889
		mu 0 3 1797 1796 1777
		f 3 -4890 4890 4891
		mu 0 3 1797 1777 1798
		f 3 4892 4893 -4892
		mu 0 3 1798 1799 1797
		f 3 4894 4895 -4894
		mu 0 3 1799 1800 1797
		f 3 4896 4897 -4896
		mu 0 3 1800 1801 1797
		f 3 4898 -4897 4899
		mu 0 3 1802 1801 1800
		f 3 4900 4901 -4900
		mu 0 3 1800 1803 1802
		f 3 4902 -4902 4903
		mu 0 3 1804 1802 1803
		f 3 4904 4905 -4904
		mu 0 3 1803 1805 1804
		f 3 4906 4907 -4906
		mu 0 3 1805 1806 1804
		f 3 -4908 4908 4909
		mu 0 3 1804 1806 1807
		f 3 -4909 4910 4911
		mu 0 3 1807 1806 1808
		f 3 4912 4913 -4911
		mu 0 3 1806 1809 1808
		f 3 -4914 4914 4915
		mu 0 3 1808 1809 1810
		f 3 4916 -4916 4917
		mu 0 3 1811 1808 1810
		f 3 -4918 4918 4919
		mu 0 3 1811 1810 1812
		f 3 4920 -4919 4921
		mu 0 3 1813 1812 1810
		f 3 4922 -4922 4923
		mu 0 3 1814 1813 1810
		f 3 4924 -4923 4925
		mu 0 3 1815 1813 1814
		f 3 4926 4927 -4926
		mu 0 3 1814 1816 1815
		f 3 4928 4929 -4928
		mu 0 3 1816 1817 1815
		f 3 -4930 4930 4931
		mu 0 3 1815 1817 1818
		f 3 4932 4933 -4931
		mu 0 3 1817 1819 1818
		f 3 4934 4935 -4934
		mu 0 3 1819 1820 1818
		f 3 -4936 4936 4937
		mu 0 3 1818 1820 1821
		f 3 4938 -4938 4939
		mu 0 3 1822 1818 1821
		f 3 -4940 4940 4941
		mu 0 3 1822 1821 1823
		f 3 4942 -4942 4943
		mu 0 3 1824 1822 1823
		f 3 4944 -4944 4945
		mu 0 3 1812 1824 1823
		f 3 -4946 4946 4947
		mu 0 3 1812 1823 1825
		f 3 -4947 4948 4949
		mu 0 3 1825 1823 1826
		f 3 4950 -4950 4951
		mu 0 3 1827 1825 1826
		f 3 4952 -4952 4953
		mu 0 3 1828 1827 1826
		f 3 -4954 4954 4955
		mu 0 3 1828 1826 1829
		f 3 4956 4957 -4956
		mu 0 3 1829 1830 1828
		f 3 -4958 4958 4959
		mu 0 3 1828 1830 1831
		f 3 -4959 4960 4961
		mu 0 3 1831 1830 1832
		f 3 -4962 4962 4963
		mu 0 3 1831 1832 1833
		f 3 -4964 4964 4965
		mu 0 3 1831 1833 1834
		f 3 4966 4967 -4965
		mu 0 3 1833 1811 1834
		f 3 4968 4969 -4968
		mu 0 3 1811 1828 1834
		f 3 4970 -4967 4971
		mu 0 3 1835 1811 1833
		f 3 -4972 4972 4973
		mu 0 3 1835 1833 1836
		f 3 4974 -4974 4975
		mu 0 3 1837 1835 1836
		f 3 -4976 4976 4977
		mu 0 3 1837 1836 1838
		f 3 -4977 4978 4979
		mu 0 3 1838 1836 1839
		f 3 4980 -4979 4981
		mu 0 3 1840 1839 1836
		f 3 4982 4983 -4982
		mu 0 3 1836 1832 1840
		f 3 4984 4985 -4984
		mu 0 3 1832 1841 1840
		f 3 -4986 4986 4987
		mu 0 3 1840 1841 1842
		f 3 4988 4989 -4987
		mu 0 3 1841 1843 1842
		f 3 4990 4991 -4990
		mu 0 3 1843 1844 1842
		f 3 4992 4993 -4991
		mu 0 3 1843 1845 1844
		f 3 4994 4995 -4994
		mu 0 3 1845 1846 1844
		f 3 4996 4997 -4996
		mu 0 3 1846 1839 1844
		f 3 4998 -4997 4999
		mu 0 3 1847 1839 1846
		f 3 -5000 5000 5001
		mu 0 3 1847 1846 1848
		f 3 -5002 5002 5003
		mu 0 3 1847 1848 1849
		f 3 5004 -5004 5005
		mu 0 3 1850 1847 1849
		f 3 -5006 5006 5007
		mu 0 3 1850 1849 1851
		f 3 5008 5009 -5007
		mu 0 3 1849 1852 1851
		f 3 5010 -5010 5011
		mu 0 3 1853 1851 1852
		f 3 5012 -5012 5013
		mu 0 3 1854 1853 1852
		f 3 5014 -5014 5015
		mu 0 3 1855 1854 1852
		f 3 5016 5017 -5016
		mu 0 3 1852 1856 1855
		f 3 5018 5019 -5018
		mu 0 3 1856 1857 1855
		f 3 5020 5021 -5020
		mu 0 3 1857 1858 1855
		f 3 5022 -5022 5023
		mu 0 3 1859 1855 1858
		f 3 5024 5025 -5024
		mu 0 3 1858 1860 1859
		f 3 -5026 5026 5027
		mu 0 3 1859 1860 1861
		f 3 5028 5029 -5027
		mu 0 3 1860 1862 1861
		f 3 -5030 5030 5031
		mu 0 3 1861 1862 1863
		f 3 5032 -5032 5033
		mu 0 3 1864 1861 1863
		f 3 5034 -5034 5035
		mu 0 3 1865 1864 1863
		f 3 5036 -5036 5037
		mu 0 3 1866 1865 1863
		f 3 -5038 5038 5039
		mu 0 3 1866 1863 1867
		f 3 -5040 5040 5041
		mu 0 3 1866 1867 1868
		f 3 5042 5043 -5042
		mu 0 3 1868 1869 1866
		f 3 5044 -5044 5045
		mu 0 3 1870 1866 1869
		f 3 5046 -5046 5047
		mu 0 3 1871 1870 1869
		f 3 5048 -5048 5049
		mu 0 3 1872 1871 1869
		f 3 -5050 5050 5051
		mu 0 3 1872 1869 1873
		f 3 5052 -5052 5053
		mu 0 3 1874 1872 1873
		f 3 5054 5055 -5054
		mu 0 3 1873 1875 1874
		f 3 5056 -5056 5057
		mu 0 3 742 1874 1875
		f 3 -5055 5058 5059
		mu 0 3 1875 1873 1876
		f 3 5060 -5060 5061
		mu 0 3 1877 1875 1876
		f 3 5062 5063 -5062
		mu 0 3 1876 1878 1877
		f 3 5064 5065 -5064
		mu 0 3 1878 1879 1877
		f 3 -5066 5066 5067
		mu 0 3 1877 1879 1880
		f 3 -5067 5068 5069
		mu 0 3 1880 1879 1881
		f 3 -5070 5070 5071
		mu 0 3 1880 1881 1882
		f 3 5072 -5071 5073
		mu 0 3 1883 1882 1881
		f 3 5074 5075 -5073
		mu 0 3 1883 1884 1882
		f 3 5076 -5076 5077
		mu 0 3 1877 1882 1884
		f 3 5078 -5078 5079
		mu 0 3 739 1877 1884
		f 3 5080 -5080 5081
		mu 0 3 1885 739 1884
		f 3 5082 -5081 5083
		mu 0 3 1886 739 1885
		f 3 -5075 5084 -5082
		mu 0 3 1884 1883 1885
		f 3 -5085 5085 5086
		mu 0 3 1885 1883 1887
		f 3 -5086 5087 5088
		mu 0 3 1887 1883 1888
		f 3 5089 5090 -5088
		mu 0 3 1883 1879 1888
		f 3 -5091 5091 5092
		mu 0 3 1888 1879 1889
		f 3 5093 5094 -5092
		mu 0 3 1879 1890 1889
		f 3 -5095 5095 5096
		mu 0 3 1889 1890 1891
		f 3 5097 5098 -5096
		mu 0 3 1890 1892 1891
		f 3 5099 5100 -5098
		mu 0 3 1890 1893 1892
		f 3 5101 -5101 5102
		mu 0 3 1894 1892 1893
		f 3 5103 5104 -5103
		mu 0 3 1893 1895 1894
		f 3 5105 -5105 5106
		mu 0 3 1896 1894 1895
		f 3 5107 5108 -5107
		mu 0 3 1895 1897 1896
		f 3 5109 5110 -5109
		mu 0 3 1897 1898 1896
		f 3 5111 -5110 5112
		mu 0 3 1899 1898 1897
		f 3 5113 -5113 5114
		mu 0 3 1900 1899 1897
		f 3 5115 -5115 5116
		mu 0 3 1901 1900 1897
		f 3 5117 -5116 5118
		mu 0 3 1902 1900 1901
		f 3 5119 -5119 5120
		mu 0 3 1903 1902 1901
		f 3 -5121 5121 5122
		mu 0 3 1903 1901 1895
		f 3 -5123 5123 5124
		mu 0 3 1903 1895 1904
		f 3 -5125 5125 5126
		mu 0 3 1903 1904 1905
		f 3 5127 5128 -5127
		mu 0 3 1905 1906 1903
		f 3 5129 -5128 5130
		mu 0 3 1907 1906 1905
		f 3 5131 -5131 5132
		mu 0 3 1908 1907 1905
		f 3 -5133 5133 5134
		mu 0 3 1908 1905 1909
		f 3 5135 5136 -5135
		mu 0 3 1909 1910 1908
		f 3 -5137 5137 5138
		mu 0 3 1908 1910 1911
		f 3 5139 -5138 5140
		mu 0 3 1912 1911 1910
		f 3 5141 5142 -5141
		mu 0 3 1910 1913 1912
		f 3 5143 -5143 5144
		mu 0 3 1914 1912 1913;
	setAttr ".fc[3000:3499]"
		f 3 -5145 5145 5146
		mu 0 3 1914 1913 1915
		f 3 5147 -5147 5148
		mu 0 3 1916 1914 1915
		f 3 -5149 5149 5150
		mu 0 3 1916 1915 1917
		f 3 5151 -5151 5152
		mu 0 3 1918 1916 1917
		f 3 5153 -5153 5154
		mu 0 3 1919 1918 1917
		f 3 5155 -5155 5156
		mu 0 3 1920 1919 1917
		f 3 -5157 5157 5158
		mu 0 3 1920 1917 1921
		f 3 5159 5160 -5158
		mu 0 3 1917 1890 1921
		f 3 5161 5162 -5160
		mu 0 3 1917 1909 1890
		f 3 5163 5164 -5163
		mu 0 3 1909 1922 1890
		f 3 -5164 5165 5166
		mu 0 3 1922 1909 1893
		f 3 5167 5168 -5166
		mu 0 3 1909 1904 1893
		f 3 -5159 5169 5170
		mu 0 3 1920 1921 1876
		f 3 5171 -5156 5172
		mu 0 3 1868 1919 1920
		f 3 -5173 5173 5174
		mu 0 3 1868 1920 1873
		f 3 -5154 -5172 5175
		mu 0 3 1918 1919 1868
		f 3 5176 -5152 5177
		mu 0 3 1863 1916 1918
		f 3 5178 -5162 -5150
		mu 0 3 1915 1909 1917
		f 3 5179 5180 -5148
		mu 0 3 1916 1923 1914
		f 3 5181 5182 -5180
		mu 0 3 1916 1924 1923
		f 3 -5183 5183 5184
		mu 0 3 1923 1924 1925
		f 3 5185 5186 -5184
		mu 0 3 1924 1926 1925
		f 3 5187 5188 -5187
		mu 0 3 1926 1927 1925
		f 3 -5189 5189 5190
		mu 0 3 1925 1927 1928
		f 3 5191 5192 -5190
		mu 0 3 1927 1929 1928
		f 3 -5193 5193 5194
		mu 0 3 1928 1929 1930
		f 3 -5195 5195 5196
		mu 0 3 1928 1930 1931
		f 3 5197 -5197 5198
		mu 0 3 1911 1928 1931
		f 3 -5199 5199 5200
		mu 0 3 1911 1931 1932
		f 3 -5201 5201 5202
		mu 0 3 1911 1932 1907
		f 3 -5200 5203 5204
		mu 0 3 1932 1931 1933
		f 3 5205 5206 -5205
		mu 0 3 1933 1934 1932
		f 3 -5207 5207 5208
		mu 0 3 1932 1934 1902
		f 3 5209 -5209 5210
		mu 0 3 1906 1932 1902
		f 3 5211 -5206 5212
		mu 0 3 1935 1934 1933
		f 3 5213 -5213 5214
		mu 0 3 1936 1935 1933
		f 3 -5215 5215 5216
		mu 0 3 1936 1933 1937
		f 3 5217 -5217 5218
		mu 0 3 1938 1936 1937
		f 3 5219 -5219 5220
		mu 0 3 1939 1938 1937
		f 3 5221 5222 -5220
		mu 0 3 1939 1940 1938
		f 3 5223 5224 -5223
		mu 0 3 1940 1941 1938
		f 3 5225 5226 -5225
		mu 0 3 1941 1942 1938
		f 3 5227 5228 -5226
		mu 0 3 1941 1943 1942
		f 3 5229 5230 -5229
		mu 0 3 1943 1944 1942
		f 3 5231 5232 -5231
		mu 0 3 1944 1935 1942
		f 3 -5232 5233 5234
		mu 0 3 1935 1944 1945
		f 3 5235 5236 -5234
		mu 0 3 1944 1946 1945
		f 3 -5237 5237 5238
		mu 0 3 1945 1946 1947
		f 3 5239 -5239 5240
		mu 0 3 1900 1945 1947
		f 3 5241 -5240 5242
		mu 0 3 1934 1945 1900
		f 3 -5238 5243 5244
		mu 0 3 1947 1946 1899
		f 3 -5236 5245 5246
		mu 0 3 1946 1944 1948
		f 3 5247 -5246 -5230
		mu 0 3 1943 1948 1944
		f 3 5248 -5228 5249
		mu 0 3 1949 1943 1941
		f 3 -5250 5250 5251
		mu 0 3 1949 1941 1950
		f 3 5252 -5252 5253
		mu 0 3 1951 1949 1950
		f 3 5254 -5253 5255
		mu 0 3 1952 1949 1951
		f 3 5256 5257 -5255
		mu 0 3 1952 1953 1949
		f 3 5258 -5257 5259
		mu 0 3 1954 1953 1952
		f 3 5260 5261 -5259
		mu 0 3 1954 1955 1953
		f 3 5262 -5261 5263
		mu 0 3 1956 1955 1954
		f 3 -5249 -5258 5264
		mu 0 3 1943 1949 1953
		f 3 5265 -5251 -5224
		mu 0 3 1940 1950 1941
		f 3 -5227 5266 -5218
		mu 0 3 1938 1942 1936
		f 3 -5216 5267 5268
		mu 0 3 1937 1933 1957
		f 3 5269 -5268 5270
		mu 0 3 1958 1957 1933
		f 3 -5233 -5214 -5267
		mu 0 3 1942 1935 1936
		f 3 -5212 -5235 -5242
		mu 0 3 1934 1935 1945
		f 3 5271 -5271 -5204
		mu 0 3 1931 1958 1933
		f 3 -5272 -5196 5272
		mu 0 3 1958 1931 1930
		f 3 5273 5274 -5192
		mu 0 3 1927 1959 1929
		f 3 5275 -5274 5276
		mu 0 3 1960 1959 1927
		f 3 5277 -5277 5278
		mu 0 3 1961 1960 1927
		f 3 5279 5280 -5278
		mu 0 3 1961 1962 1960
		f 3 -5281 5281 5282
		mu 0 3 1960 1962 1963
		f 3 5283 5284 -5282
		mu 0 3 1962 1964 1963
		f 3 -5284 5285 5286
		mu 0 3 1964 1962 1965
		f 3 -5286 5287 5288
		mu 0 3 1965 1962 143
		f 3 5289 -5288 5290
		mu 0 3 1966 143 1962
		f 3 5291 -5291 5292
		mu 0 3 1967 1966 1962
		f 3 5293 -5293 5294
		mu 0 3 1968 1967 1962
		f 3 5295 -5295 5296
		mu 0 3 1969 1968 1962
		f 3 -5297 5297 5298
		mu 0 3 1969 1962 1970
		f 3 -5299 5299 5300
		mu 0 3 1969 1970 1971
		f 3 5301 5302 -5300
		mu 0 3 1970 1972 1971
		f 3 5303 5304 -5303
		mu 0 3 1972 1973 1971
		f 3 5305 -5305 5306
		mu 0 3 1974 1971 1973
		f 3 -5307 5307 5308
		mu 0 3 1974 1973 1975
		f 3 5309 -5309 5310
		mu 0 3 1816 1974 1975
		f 3 -5310 5311 5312
		mu 0 3 1974 1816 1976
		f 3 5313 5314 -5313
		mu 0 3 1976 1977 1974
		f 3 5315 5316 -5314
		mu 0 3 1976 1968 1977
		f 3 5317 5318 -5317
		mu 0 3 1968 1971 1977
		f 3 5319 -5316 5320
		mu 0 3 1978 1968 1976
		f 3 -5321 5321 5322
		mu 0 3 1978 1976 1814
		f 3 5323 5324 -5323
		mu 0 3 1814 1979 1978
		f 3 -5325 5325 5326
		mu 0 3 1978 1979 1980
		f 3 5327 5328 -5326
		mu 0 3 1979 1981 1980
		f 3 5329 5330 -5329
		mu 0 3 1981 1966 1980
		f 3 5331 -5330 5332
		mu 0 3 1982 1966 1981
		f 3 5333 5334 -5332
		mu 0 3 1982 1983 1966
		f 3 5335 -5335 5336
		mu 0 3 145 1966 1983
		f 3 5337 5338 -5334
		mu 0 3 1982 146 1983
		f 3 5339 -5333 -5328
		mu 0 3 1979 1982 1981
		f 3 5340 -5340 5341
		mu 0 3 1809 1982 1979
		f 3 5342 -5341 5343
		mu 0 3 1984 1982 1809
		f 3 -5344 5344 5345
		mu 0 3 1984 1809 1985
		f 3 5346 -5346 5347
		mu 0 3 151 1984 1985
		f 3 5348 -5348 5349
		mu 0 3 1986 151 1985
		f 3 5350 -5350 5351
		mu 0 3 1805 1986 1985
		f 3 -5351 5352 5353
		mu 0 3 1986 1805 1987
		f 3 5354 -5354 5355
		mu 0 3 156 1986 1987
		f 3 5356 5357 -5356
		mu 0 3 1987 1988 156
		f 3 5358 5359 -5357
		mu 0 3 1987 1989 1988
		f 3 -5360 5360 5361
		mu 0 3 1988 1989 164
		f 3 5362 -5362 5363
		mu 0 3 158 1988 164
		f 3 5364 5365 -5361
		mu 0 3 1989 1990 164
		f 3 5366 5367 -5365
		mu 0 3 1989 1991 1990
		f 3 -5368 5368 5369
		mu 0 3 1990 1991 1799
		f 3 -5370 5370 5371
		mu 0 3 1990 1799 1992
		f 3 -5372 5372 5373
		mu 0 3 1990 1992 1993
		f 3 5374 -5374 5375
		mu 0 3 165 1990 1993
		f 3 -5373 5376 5377
		mu 0 3 1993 1992 1798
		f 3 -5378 5378 5379
		mu 0 3 1993 1798 1775
		f 3 -5380 5380 5381
		mu 0 3 1993 1775 167
		f 3 5382 -5367 -5359
		mu 0 3 1987 1991 1989
		f 3 5383 5384 -5383
		mu 0 3 1987 1803 1991
		f 3 -5343 5385 5386
		mu 0 3 1982 1984 150
		f 3 5387 -5342 -5324
		mu 0 3 1814 1809 1979
		f 3 -5327 5388 -5320
		mu 0 3 1978 1980 1968
		f 3 -5308 5389 5390
		mu 0 3 1975 1973 1994
		f 3 -5391 5391 5392
		mu 0 3 1975 1994 1819
		f 3 5393 5394 -5392
		mu 0 3 1994 1995 1819
		f 3 5395 -5394 -5390
		mu 0 3 1973 1995 1994
		f 3 -5306 -5315 -5319
		mu 0 3 1971 1974 1977
		f 3 5396 -5396 -5304
		mu 0 3 1972 1995 1973
		f 3 5397 5398 -5397
		mu 0 3 1972 1996 1995
		f 3 -5399 5399 5400
		mu 0 3 1995 1996 1820
		f 3 5401 5402 -5400
		mu 0 3 1996 1970 1820
		f 3 5403 5404 -5403
		mu 0 3 1970 1852 1820
		f 3 5405 -5405 5406
		mu 0 3 1997 1820 1852
		f 3 -5302 -5402 -5398
		mu 0 3 1972 1970 1996
		f 3 5407 5408 -5298
		mu 0 3 1962 1998 1970
		f 3 5409 5410 -5409
		mu 0 3 1998 1857 1970
		f 3 -5410 5411 5412
		mu 0 3 1857 1998 1999
		f 3 -5413 5413 5414
		mu 0 3 1857 1999 2000
		f 3 5415 -5414 5416
		mu 0 3 1962 2000 1999
		f 3 5417 -5415 5418
		mu 0 3 2001 1857 2000
		f 3 -5419 5419 5420
		mu 0 3 2001 2000 2002
		f 3 -5421 5421 5422
		mu 0 3 2001 2002 2003
		f 3 -5423 5423 5424
		mu 0 3 2001 2003 2004
		f 3 -5424 5425 5426
		mu 0 3 2004 2003 2005
		f 3 5427 5428 -5426
		mu 0 3 2003 1926 2005
		f 3 5429 5430 -5429
		mu 0 3 1926 1862 2005
		f 3 5431 5432 -5431
		mu 0 3 1862 2006 2005
		f 3 5433 -5428 5434
		mu 0 3 2007 1926 2003
		f 3 5435 -5434 5436
		mu 0 3 1961 1926 2007
		f 3 5437 -5437 5438
		mu 0 3 2002 1961 2007
		f 3 -5427 -5433 5439
		mu 0 3 2004 2005 2006
		f 3 5440 -5440 5441
		mu 0 3 1858 2004 2006
		f 3 -5425 -5441 5442
		mu 0 3 2001 2004 1858
		f 3 -5439 -5435 -5422
		mu 0 3 2002 2007 2003
		f 3 5443 -5438 -5420
		mu 0 3 2000 1961 2002
		f 3 -5417 -5412 -5408
		mu 0 3 1962 1999 1998
		f 3 -5296 -5301 -5318
		mu 0 3 1968 1969 1971
		f 3 -5389 5444 -5294
		mu 0 3 1968 1980 1967
		f 3 -5331 -5292 -5445
		mu 0 3 1980 1966 1967
		f 3 -5444 -5416 -5280
		mu 0 3 1961 2000 1962
		f 3 5445 -5276 -5283
		mu 0 3 1963 1959 1960
		f 3 -5279 -5188 -5436
		mu 0 3 1961 1927 1926
		f 3 -5186 5446 -5430
		mu 0 3 1926 1924 1862
		f 3 5447 -5185 -5191
		mu 0 3 1928 1923 1925
		f 3 5448 5449 -5448
		mu 0 3 1928 1912 1923
		f 3 -5182 5450 -5447
		mu 0 3 1924 1916 1862
		f 3 -5181 -5450 -5144
		mu 0 3 1914 1923 1912
		f 3 -5142 5451 -5146
		mu 0 3 1913 1910 1915
		f 3 -5198 -5140 -5449
		mu 0 3 1928 1911 1912
		f 3 -5179 -5452 -5136
		mu 0 3 1909 1915 1910
		f 3 -5139 -5203 -5132
		mu 0 3 1908 1911 1907
		f 3 -5202 -5210 -5130
		mu 0 3 1907 1932 1906
		f 3 -5134 -5126 -5168
		mu 0 3 1909 1905 1904
		f 3 -5211 -5120 -5129
		mu 0 3 1906 1902 1903
		f 3 -5208 -5243 -5118
		mu 0 3 1902 1934 1900
		f 3 -5245 -5114 -5241
		mu 0 3 1947 1899 1900
		f 3 -5122 -5117 -5108
		mu 0 3 1895 1901 1897
		f 3 -5124 -5104 -5169
		mu 0 3 1904 1895 1893
		f 3 -5167 -5100 -5165
		mu 0 3 1922 1893 1890
		f 3 -5161 -5094 5452
		mu 0 3 1921 1890 1879
		f 3 -5093 -5097 5453
		mu 0 3 1888 1889 1891
		f 3 -5074 -5069 -5090
		mu 0 3 1883 1881 1879
		f 3 -5077 -5068 -5072
		mu 0 3 1882 1877 1880
		f 3 -5065 5454 -5453
		mu 0 3 1879 1878 1921
		f 3 -5170 -5455 -5063
		mu 0 3 1876 1921 1878
		f 3 5455 -5061 5456
		mu 0 3 740 1875 1877
		f 3 -5171 -5059 -5174
		mu 0 3 1920 1876 1873
		f 3 -5057 5457 -5053
		mu 0 3 1874 742 1872
		f 3 5458 5459 -5458
		mu 0 3 742 765 1872
		f 3 5460 5461 -5460
		mu 0 3 765 2008 1872
		f 3 5462 -5049 -5462
		mu 0 3 2008 1871 1872
		f 3 -5463 5463 5464
		mu 0 3 1871 2008 2009
		f 3 5465 5466 -5464
		mu 0 3 2008 1850 2009
		f 3 -5467 5467 5468
		mu 0 3 2009 1850 1853
		f 3 5469 -5469 5470
		mu 0 3 1870 2009 1853
		f 3 5471 5472 -5466
		mu 0 3 2008 2010 1850
		f 3 5473 5474 -5473
		mu 0 3 2010 1838 1850
		f 3 5475 5476 -5474
		mu 0 3 2010 2011 1838
		f 3 5477 5478 -5477
		mu 0 3 2011 793 1838
		f 3 5479 -5479 5480
		mu 0 3 2012 1838 793
		f 3 5481 5482 -5481
		mu 0 3 793 2013 2012
		f 3 -5483 5483 5484
		mu 0 3 2012 2013 1793
		f 3 5485 5486 -5484
		mu 0 3 2013 2014 1793
		f 3 5487 -5486 5488
		mu 0 3 2015 2014 2013
		f 3 5489 -5489 5490
		mu 0 3 794 2015 2013
		f 3 5491 -5490 5492
		mu 0 3 2016 2015 794
		f 3 5493 -5492 5494
		mu 0 3 2017 2015 2016
		f 3 5495 5496 -5495
		mu 0 3 2016 2018 2017
		f 3 5497 5498 -5497
		mu 0 3 2018 2019 2017
		f 3 -5499 5499 5500
		mu 0 3 2017 2019 2020
		f 3 5501 5502 -5501
		mu 0 3 2020 2021 2017
		f 3 -5502 5503 5504
		mu 0 3 2021 2020 2014
		f 3 -5500 5505 -5504
		mu 0 3 2020 2019 2014
		f 3 5506 -5506 5507
		mu 0 3 1792 2014 2019
		f 3 -5498 5508 5509
		mu 0 3 2019 2018 2022
		f 3 5510 -5510 5511
		mu 0 3 1788 2019 2022
		f 3 -5509 5512 5513
		mu 0 3 2022 2018 2023
		f 3 5514 5515 -5513
		mu 0 3 2018 2024 2023
		f 3 5516 5517 -5516
		mu 0 3 2024 2025 2023
		f 3 5518 5519 -5518
		mu 0 3 2025 2026 2023
		f 3 5520 -5520 5521
		mu 0 3 2027 2023 2026
		f 3 -5522 5522 5523
		mu 0 3 2027 2026 2028
		f 3 5524 5525 -5524
		mu 0 3 2028 2029 2027
		f 3 5526 -5526 5527
		mu 0 3 2022 2027 2029
		f 3 -5528 5528 5529
		mu 0 3 2022 2029 1786
		f 3 5530 5531 -5525
		mu 0 3 2028 845 2029
		f 3 5532 -5532 5533
		mu 0 3 1785 2029 845
		f 3 -5534 5534 5535
		mu 0 3 1785 845 2030
		f 3 5536 5537 -5523
		mu 0 3 2026 2031 2028
		f 3 -5538 5538 5539
		mu 0 3 2028 2031 843
		f 3 5540 5541 -5537
		mu 0 3 2026 2032 2031
		f 3 5542 -5542 5543
		mu 0 3 839 2031 2032
		f 3 5544 -5541 5545
		mu 0 3 2033 2032 2026
		f 3 5546 -5545 5547
		mu 0 3 2034 2032 2033
		f 3 -5548 5548 5549
		mu 0 3 2034 2033 797
		f 3 -5550 5550 5551
		mu 0 3 2034 797 801
		f 3 5552 5553 -5552
		mu 0 3 801 835 2034
		f 3 -5549 5554 5555
		mu 0 3 797 2033 2035
		f 3 -5555 5556 5557
		mu 0 3 2035 2033 2025
		f 3 5558 5559 -5547
		mu 0 3 2034 837 2032
		f 3 -5557 -5546 -5519
		mu 0 3 2025 2033 2026
		f 3 -5558 -5517 5560
		mu 0 3 2035 2025 2024
		f 3 5561 -5561 5562
		mu 0 3 796 2035 2024
		f 3 5563 5564 -5563
		mu 0 3 2024 2036 796
		f 3 -5565 5565 5566
		mu 0 3 796 2036 2016
		f 3 -5564 -5515 5567
		mu 0 3 2036 2024 2018
		f 3 -5521 -5527 -5514
		mu 0 3 2023 2027 2022
		f 3 -5568 -5496 -5566
		mu 0 3 2036 2018 2016
		f 3 -5494 -5503 5568
		mu 0 3 2015 2017 2021
		f 3 -5505 -5488 -5569
		mu 0 3 2021 2014 2015
		f 3 -5485 5569 5570
		mu 0 3 2012 1793 1837
		f 3 -5478 5571 5572
		mu 0 3 793 2011 771
		f 3 -5476 5573 5574
		mu 0 3 2011 2010 768
		f 3 -5472 5575 -5574
		mu 0 3 2010 2008 768
		f 3 -5047 -5465 -5470
		mu 0 3 1870 1871 2009
		f 3 -5471 5576 -5045
		mu 0 3 1870 1853 1866
		f 3 -5051 -5043 -5175
		mu 0 3 1873 1869 1868
		f 3 5577 -5176 -5041
		mu 0 3 1867 1918 1868
		f 3 -5578 -5039 -5178
		mu 0 3 1918 1867 1863
		f 3 5578 -5037 -5577
		mu 0 3 1853 1865 1866
		f 3 5579 5580 -5035
		mu 0 3 1865 1854 1864
		f 3 5581 5582 -5581
		mu 0 3 1854 1859 1864
		f 3 -5031 -5451 -5177
		mu 0 3 1863 1862 1916
		f 3 5583 -5432 -5029
		mu 0 3 1860 2006 1862
		f 3 -5583 -5028 -5033
		mu 0 3 1864 1859 1861
		f 3 -5442 -5584 -5025
		mu 0 3 1858 2006 1860
		f 3 -5443 -5021 -5418
		mu 0 3 2001 1858 1857
		f 3 -5411 -5019 5584
		mu 0 3 1970 1857 1856
		f 3 -5585 -5017 -5404
		mu 0 3 1970 1856 1852
		f 3 -5582 -5015 -5023
		mu 0 3 1859 1854 1855
		f 3 -5580 -5579 -5013
		mu 0 3 1854 1865 1853
		f 3 -5407 -5009 5585
		mu 0 3 1997 1852 1849
		f 3 5586 -5586 5587
		mu 0 3 2037 1997 1849
		f 3 5588 5589 -5587
		mu 0 3 2037 1821 1997
		f 3 -5468 -5008 -5011
		mu 0 3 1853 1850 1851
		f 3 5590 -5005 -5475
		mu 0 3 1838 1847 1850
		f 3 5591 -5588 -5003
		mu 0 3 1848 2037 1849
		f 3 -5592 5592 5593
		mu 0 3 2037 1848 1826
		f 3 -4995 5594 -5001
		mu 0 3 1846 1845 1848
		f 3 -5595 5595 5596
		mu 0 3 1848 1845 2038
		f 3 -5596 5597 5598
		mu 0 3 2038 1845 1830
		f 3 -5597 5599 5600
		mu 0 3 1848 2038 1829
		f 3 -4993 5601 -5598
		mu 0 3 1845 1843 1830
		f 3 5602 -5602 -4989
		mu 0 3 1841 1830 1843
		f 3 -4992 5603 -4988
		mu 0 3 1842 1844 1840
		f 3 -5604 -4998 -4981
		mu 0 3 1840 1844 1839
		f 3 -4999 -5591 -4980
		mu 0 3 1839 1847 1838
		f 3 -4978 -5480 -5571
		mu 0 3 1837 1838 2012
		f 3 5604 5605 -4975
		mu 0 3 1837 2039 1835
		f 3 5606 5607 -5606
		mu 0 3 2039 1808 1835
		f 3 5608 -5607 5609
		mu 0 3 2040 1808 2039
		f 3 -5610 5610 5611
		mu 0 3 2040 2039 2041
		f 3 -5612 5612 5613
		mu 0 3 2040 2041 2042
		f 3 -5614 5614 5615
		mu 0 3 2040 2042 1801
		f 3 5616 -5616 5617
		mu 0 3 2043 2040 1801
		f 3 5618 5619 -5617
		mu 0 3 2043 1807 2040
		f 3 5620 -5619 5621
		mu 0 3 1802 1807 2043
		f 3 5622 -5615 5623
		mu 0 3 1796 1801 2042
		f 3 5624 5625 -5613
		mu 0 3 2041 1795 2042
		f 3 -5605 5626 -5611
		mu 0 3 2039 1837 2041
		f 3 5627 5628 -5627
		mu 0 3 1837 1794 2041
		f 3 -4963 -4983 -4973
		mu 0 3 1833 1832 1836
		f 3 -4961 -5603 -4985
		mu 0 3 1832 1830 1841
		f 3 -4966 -4970 -4960
		mu 0 3 1831 1834 1828
		f 3 -5599 -4957 -5600
		mu 0 3 2038 1830 1829
		f 3 -5601 -4955 -5593
		mu 0 3 1848 1829 1826
		f 3 -4953 -4969 5629
		mu 0 3 1827 1828 1811
		f 3 -4951 -5630 5630
		mu 0 3 1825 1827 1811
		f 3 5631 -5594 -4949
		mu 0 3 1823 2037 1826
		f 3 -4941 -5589 -5632
		mu 0 3 1823 1821 2037
		f 3 5632 -4939 -4943
		mu 0 3 1824 1818 1822
		f 3 5633 -5633 5634
		mu 0 3 1813 1818 1824
		f 3 -4937 -5406 -5590
		mu 0 3 1821 1820 1997
		f 3 -5395 -5401 -4935
		mu 0 3 1819 1995 1820
		f 3 5635 -5393 -4933
		mu 0 3 1817 1975 1819
		f 3 -4929 -5311 -5636
		mu 0 3 1817 1816 1975
		f 3 -5322 -5312 -4927
		mu 0 3 1814 1976 1816
		f 3 -4932 -5634 -4925
		mu 0 3 1815 1818 1813
		f 3 -4945 -4921 -5635
		mu 0 3 1824 1812 1813
		f 3 -4948 -5631 -4920
		mu 0 3 1812 1825 1811
		f 3 -5608 -4917 -4971
		mu 0 3 1835 1808 1811
		f 3 -4915 -5388 -4924
		mu 0 3 1810 1809 1814
		f 3 -5345 -4913 5636
		mu 0 3 1985 1809 1806
		f 3 -4912 -5609 -5620
		mu 0 3 1807 1808 2040
		f 3 -5352 -5637 -4907
		mu 0 3 1805 1985 1806
		f 3 -4905 -5384 -5353
		mu 0 3 1805 1803 1987
		f 3 -4910 -5621 -4903
		mu 0 3 1804 1807 1802
		f 3 -5385 -4901 5637
		mu 0 3 1991 1803 1800
		f 3 -4899 -5622 -5618
		mu 0 3 1801 1802 2043
		f 3 -5638 -4895 -5369
		mu 0 3 1991 1800 1799
		f 3 -4893 -5377 -5371
		mu 0 3 1799 1798 1992
		f 3 -5623 -4889 -4898
		mu 0 3 1801 1796 1797
		f 3 -5624 -5626 -4885
		mu 0 3 1796 2042 1795
		f 3 -4883 -5625 -5629
		mu 0 3 1794 1795 2041
		f 3 -5570 -4882 -5628
		mu 0 3 1837 1793 1794
		f 3 -5507 -4879 -5487
		mu 0 3 2014 1792 1793
		f 3 5638 -4877 -5508
		mu 0 3 2019 1790 1792
		f 3 -4871 -5639 -5511
		mu 0 3 1788 1790 2019
		f 3 -5512 -5530 -4865
		mu 0 3 1788 2022 1786
		f 3 -5529 -5533 -4861
		mu 0 3 1786 2029 1785
		f 3 -4859 -5536 5639
		mu 0 3 1783 1785 2030
		f 3 5640 5641 -5640
		mu 0 3 2030 848 1783
		f 3 -4864 -4857 5642
		mu 0 3 1787 1784 1782
		f 3 5643 5644 -4855
		mu 0 3 1783 850 1770
		f 3 -4867 -5643 -4851
		mu 0 3 1781 1787 1782
		f 3 5645 -4869 -4849
		mu 0 3 1779 1789 1781
		f 3 -4875 -5646 -4843
		mu 0 3 1778 1789 1779
		f 3 -4876 -4841 -4887
		mu 0 3 1791 1778 1777
		f 3 -4839 -5379 -4891
		mu 0 3 1777 1775 1798
		f 3 -5381 -4835 5646
		mu 0 3 167 1775 1773
		f 3 -4838 -4846 -4833
		mu 0 3 1774 1776 1772
		f 3 5647 -5647 -4831
		mu 0 3 171 167 1773
		f 3 -4854 -4827 -4848
		mu 0 3 1780 1770 1772
		f 3 -4817 5648 -4825
		mu 0 3 1769 1767 176
		f 3 -4815 -4819 -5645
		mu 0 3 850 1768 1770
		f 3 -1922 -5644 -5642
		mu 0 3 848 850 1783
		f 3 -1936 -1930 -1919
		mu 0 3 847 854 849
		f 3 -1918 -5641 5649
		mu 0 3 846 848 2030
		f 3 -1935 -1915 5650
		mu 0 3 856 847 844
		f 3 -1914 -5650 -5535
		mu 0 3 845 846 2030
		f 3 -5540 -1911 -5531
		mu 0 3 2028 843 845
		f 3 -2037 -5651 -1909
		mu 0 3 842 856 844
		f 3 5651 -1907 -5539
		mu 0 3 2031 841 843
		f 3 -2030 -2036 -1905
		mu 0 3 840 891 842
		f 3 -5652 -5543 -1903
		mu 0 3 841 2031 839
		f 3 -2031 -1901 -2024
		mu 0 3 888 840 838
		f 3 -5544 -5560 -1900
		mu 0 3 839 2032 837
		f 3 -5554 -1896 -5559
		mu 0 3 2034 835 837
		f 3 -1898 -1893 -2023
		mu 0 3 838 836 834
		f 3 -2021 -1887 -2014
		mu 0 3 887 834 831
		f 3 -1876 -1871 -2012
		mu 0 3 831 829 828
		f 3 -2010 -1869 -2007
		mu 0 3 886 828 827
		f 3 -1873 5652 -1863
		mu 0 3 826 830 824
		f 3 -1861 5653 5654
		mu 0 3 825 822 2044
		f 3 5655 -5655 5656
		mu 0 3 714 825 2044
		f 3 -1883 -1859 -5653
		mu 0 3 830 823 824
		f 3 -5654 -1855 5657
		mu 0 3 2044 822 715
		f 3 -1858 -1886 -1851
		mu 0 3 821 823 820
		f 3 -1885 5658 -1849
		mu 0 3 820 833 807
		f 3 -1847 5659 -1853
		mu 0 3 819 808 715
		f 3 -1881 -1804 -5659
		mu 0 3 833 805 807
		f 3 -1890 -1800 -1880
		mu 0 3 832 804 805
		f 3 -1892 5660 -1798
		mu 0 3 804 835 803
		f 3 -5661 -5553 -1796
		mu 0 3 803 835 801
		f 3 -1803 -1794 -1845
		mu 0 3 806 802 800
		f 3 -1790 -1826 -1839
		mu 0 3 800 798 816
		f 3 -1788 -1793 -5551
		mu 0 3 797 799 801
		f 3 -5556 -5562 -1784
		mu 0 3 797 2035 796
		f 3 -5567 -5493 -1782
		mu 0 3 796 2016 794
		f 3 -1787 -1780 5661
		mu 0 3 798 795 789
		f 3 -5491 -5482 -1776
		mu 0 3 794 2013 793
		f 3 -1775 -5573 5662
		mu 0 3 791 793 771
		f 3 -1766 5663 5664
		mu 0 3 786 777 781
		f 3 -1779 -1772 -1764
		mu 0 3 789 792 790
		f 3 -1830 -5662 -1762
		mu 0 3 788 798 789
		f 3 5665 -1831 -1760
		mu 0 3 787 817 788
		f 3 -1835 -5666 -1758
		mu 0 3 785 817 787
		f 3 -5665 -1740 -1757
		mu 0 3 786 781 782
		f 3 -1739 -5664 -1730
		mu 0 3 778 781 777
		f 3 -1728 -1769 -1719
		mu 0 3 775 777 773
		f 3 -1771 -5663 -1713
		mu 0 3 773 791 771
		f 3 -5575 -1709 -5572
		mu 0 3 2011 768 771
		f 3 -1707 5666 -1711
		mu 0 3 770 769 772
		f 3 -1717 -5667 -1705
		mu 0 3 767 772 769
		f 3 -5461 -1703 -5576
		mu 0 3 2008 765 768
		f 3 -1718 -1701 -1722
		mu 0 3 774 767 766
		f 3 5667 -1723 -1699
		mu 0 3 764 776 766
		f 3 -1725 -5668 -1695
		mu 0 3 763 776 764
		f 3 -1690 5668 5669
		mu 0 3 760 762 744
		f 3 -1687 -1734 -1691
		mu 0 3 761 759 763
		f 3 -1685 5670 5671
		mu 0 3 754 760 747
		f 3 -1681 -1742 -1736
		mu 0 3 759 758 780
		f 3 -1744 -1679 5672
		mu 0 3 783 758 756
		f 3 -5673 -1675 5673
		mu 0 3 783 756 753
		f 3 -1678 -1683 -1673
		mu 0 3 755 757 754
		f 3 -1748 -5674 -1669
		mu 0 3 727 783 753
		f 3 -5672 -1661 -1672
		mu 0 3 754 747 751
		f 3 5674 -1648 -5671
		mu 0 3 760 745 747
		f 3 -5670 -1644 -5675
		mu 0 3 760 744 745
		f 3 -1694 -1640 -5669
		mu 0 3 762 743 744
		f 3 -1698 -5459 -1638
		mu 0 3 743 765 742
		f 3 -1637 -5058 -5456
		mu 0 3 740 742 1875
		f 3 -5457 -5079 -1632
		mu 0 3 740 1877 739
		f 3 5675 -1631 -5083
		mu 0 3 1886 738 739
		f 3 -5676 5676 5677
		mu 0 3 738 1886 2045
		f 3 5678 5679 -5677
		mu 0 3 1886 2046 2045
		f 3 5680 -5680 5681
		mu 0 3 734 2045 2046
		f 3 -1629 -5678 5682
		mu 0 3 735 738 2045
		f 3 -1635 -1626 -1642
		mu 0 3 741 737 736
		f 3 -1624 -1654 -1646
		mu 0 3 736 733 746
		f 3 -1622 -5683 -5681
		mu 0 3 734 735 2045
		f 3 -1659 -1657 -1618
		mu 0 3 730 750 733
		f 3 -1665 -1660 -1612
		mu 0 3 728 748 730
		f 3 -1666 -1608 -1668
		mu 0 3 752 728 727
		f 3 -1606 -1602 -1750
		mu 0 3 727 725 723
		f 3 -1753 -1751 -1598
		mu 0 3 722 784 723
		f 3 -1836 -1754 -1596
		mu 0 3 721 785 722
		f 3 -1821 -1834 -1594
		mu 0 3 720 814 721
		f 3 -1813 -1592 5683
		mu 0 3 808 720 717
		f 3 -5660 -5684 -1586
		mu 0 3 715 808 717
		f 3 5684 5685 -1584
		mu 0 3 716 2047 713
		f 3 5686 5687 -5686
		mu 0 3 2047 2048 713
		f 3 -5657 -5658 -1582
		mu 0 3 714 2044 715
		f 3 5688 -5656 -1580
		mu 0 3 712 825 714
		f 3 -5688 5689 -1579
		mu 0 3 713 2048 711
		f 3 -1865 -5689 -1576
		mu 0 3 704 825 712
		f 3 -2008 -1868 -1552
		mu 0 3 703 827 704
		f 3 -1999 -2006 -1550
		mu 0 3 701 884 703
		f 3 -1994 -2000 -1546
		mu 0 3 699 882 701
		f 3 -1549 -1563 -1544
		mu 0 3 700 702 697
		f 3 -2045 -1993 -1542
		mu 0 3 698 879 699
		f 3 -1540 -2059 -2056
		mu 0 3 698 696 874
		f 3 5690 -2060 -1536
		mu 0 3 692 872 696
		f 3 -1535 -1539 -1564
		mu 0 3 694 695 697
		f 3 -1533 -1569 5691
		mu 0 3 608 694 710
		f 3 -5691 -1522 -1972
		mu 0 3 872 692 691
		f 3 -2061 -1520 -4716
		mu 0 3 895 691 689
		f 3 -4690 -4717 -1516
		mu 0 3 688 1746 689
		f 3 -4692 -1514 -4712
		mu 0 3 1747 688 684
		f 3 -1519 -1531 -1512
		mu 0 3 687 690 686
		f 3 -1510 -1530 5692
		mu 0 3 685 686 693
		f 3 -1508 -5693 5693
		mu 0 3 632 685 693
		f 3 -5694 5694 5695
		mu 0 3 632 693 612
		f 3 -5696 5696 5697
		mu 0 3 632 612 620
		f 3 5698 -4713 -1504
		mu 0 3 682 1750 684
		f 3 5699 -5699 -1500
		mu 0 3 681 1750 682
		f 3 -1498 -4701 -5700
		mu 0 3 681 680 1750
		f 3 5700 -4705 -1496
		mu 0 3 679 1752 680
		f 3 -4707 -5701 -1492
		mu 0 3 677 1752 679
		f 3 -1495 5701 -1491
		mu 0 3 678 633 674
		f 3 5702 -5702 5703
		mu 0 3 660 674 633
		f 3 -4677 -4708 -1488
		mu 0 3 676 1740 677
		f 3 -4666 -4673 -1486
		mu 0 3 675 932 676
		f 3 -4668 -1485 -1478
		mu 0 3 672 675 673
		f 3 -2157 -4669 -1476
		mu 0 3 671 933 672
		f 3 -2160 -1474 -4663
		mu 0 3 934 671 669
		f 3 -2172 -4664 -1468
		mu 0 3 668 939 669
		f 3 -2174 -1466 -1462
		mu 0 3 665 668 666
		f 3 -2176 -1460 -2700
		mu 0 3 940 665 664
		f 3 -1458 -2674 -2698
		mu 0 3 664 659 1110
		f 3 -1465 -1473 -1456
		mu 0 3 663 667 662
		f 3 -1480 -1454 -1472
		mu 0 3 670 661 662
		f 3 -5703 -1452 -1483
		mu 0 3 674 660 661
		f 3 -2672 -1446 -2663
		mu 0 3 1106 659 658
		f 3 5704 -2662 -1444
		mu 0 3 652 1108 658
		f 3 5705 -1433 5706
		mu 0 3 2049 653 640
		f 3 5707 -5706 5708
		mu 0 3 647 653 2049
		f 3 -1430 -1443 -1436
		mu 0 3 654 652 656
		f 3 5709 -1428 -5708
		mu 0 3 647 651 653
		f 3 -1426 -2665 -5705
		mu 0 3 652 650 1108
		f 3 -2718 -2667 -1422
		mu 0 3 648 1109 650
		f 3 -1421 -1425 -5710
		mu 0 3 647 649 651;
	setAttr ".fc[3500:3999]"
		f 3 -2717 -1418 -2726
		mu 0 3 1118 648 646
		f 3 -1417 -5709 5710
		mu 0 3 645 647 2049
		f 3 -2734 -2727 -1414
		mu 0 3 644 1121 646
		f 3 -5711 5711 -1412
		mu 0 3 645 2049 641
		f 3 -2737 -1410 -4645
		mu 0 3 1125 644 643
		f 3 -1408 -4627 -4642
		mu 0 3 643 642 1737
		f 3 -5712 -5707 -1404
		mu 0 3 641 2049 640
		f 3 -1403 -1435 -1441
		mu 0 3 638 640 655
		f 3 -1400 -4628 -1406
		mu 0 3 639 637 642
		f 3 -1399 -1440 5712
		mu 0 3 636 638 657
		f 3 5713 -4624 -1396
		mu 0 3 635 1735 637
		f 3 5714 -5714 5715
		mu 0 3 629 1735 635
		f 3 -5713 -1450 -1395
		mu 0 3 636 657 634
		f 3 -1391 -1451 -5704
		mu 0 3 633 634 660
		f 3 -1507 -1388 -1503
		mu 0 3 683 632 633
		f 3 -1386 5716 5717
		mu 0 3 630 632 2050
		f 3 -5717 5718 5719
		mu 0 3 2050 632 2051
		f 3 5720 -5720 5721
		mu 0 3 628 2050 2051
		f 3 5722 -5722 5723
		mu 0 3 622 628 2051
		f 3 -5719 5724 5725
		mu 0 3 2051 632 621
		f 3 -1392 -1384 -5716
		mu 0 3 635 631 629
		f 3 -1382 -5718 -5721
		mu 0 3 628 630 2050
		f 3 -4617 -5715 -1380
		mu 0 3 627 1735 629
		f 3 -2794 -4618 -1376
		mu 0 3 625 1152 627
		f 3 -1379 5726 -1374
		mu 0 3 626 628 624
		f 3 -1372 5727 -2797
		mu 0 3 625 623 1153
		f 3 -5727 -5723 -1370
		mu 0 3 624 628 622
		f 3 -5728 -1368 5728
		mu 0 3 1153 623 619
		f 3 -5724 -5726 -1366
		mu 0 3 622 2051 621
		f 3 -5725 -5698 -1364
		mu 0 3 621 632 620
		f 3 -1358 5729 -5729
		mu 0 3 619 617 1153
		f 3 -2800 -5730 -1354
		mu 0 3 616 1153 617
		f 3 -4597 -2801 -1352
		mu 0 3 615 1154 616
		f 3 -4595 -1350 -4610
		mu 0 3 1730 615 610
		f 3 -1357 -1361 -1348
		mu 0 3 614 618 613
		f 3 -1347 -1362 -5697
		mu 0 3 612 613 620
		f 3 -1529 -1345 -5695
		mu 0 3 693 611 612
		f 3 -4611 -1340 -4607
		mu 0 3 1732 610 599
		f 3 -1527 -1338 -1343
		mu 0 3 611 608 609
		f 3 -1571 -1336 -5692
		mu 0 3 710 607 608
		f 3 -4609 -4606 -1312
		mu 0 3 598 1733 599
		f 3 -4601 -4608 -1310
		mu 0 3 596 1731 598
		f 3 -1308 5730 5731
		mu 0 3 595 597 591
		f 3 -4587 -4600 -1306
		mu 0 3 594 1728 596
		f 3 -2819 -4586 -1302
		mu 0 3 593 1161 594
		f 3 -1304 -5732 -1298
		mu 0 3 592 595 591
		f 3 -1322 -1297 -5731
		mu 0 3 597 587 591
		f 3 -2823 -1301 -1294
		mu 0 3 589 593 590
		f 3 -1292 5732 -4582
		mu 0 3 589 588 1169
		f 3 -2839 -5733 -1290
		mu 0 3 586 1169 588
		f 3 5733 -1289 -1324
		mu 0 3 604 585 587
		f 3 -1286 -2835 -2840
		mu 0 3 586 583 1168
		f 3 -1285 -5734 -1330
		mu 0 3 584 585 604
		f 3 -1329 5734 -1282
		mu 0 3 584 605 582
		f 3 -2843 -2836 -1280
		mu 0 3 581 1167 583
		f 3 -2844 -1276 -4557
		mu 0 3 1170 581 579
		f 3 5735 -4556 -1272
		mu 0 3 577 1725 579
		f 3 5736 -5736 5737
		mu 0 3 2052 1725 577
		f 3 5738 -5737 5739
		mu 0 3 572 1725 2052
		f 3 -5739 5740 5741
		mu 0 3 1725 572 567
		f 3 5742 -5738 -1268
		mu 0 3 574 2052 577
		f 3 5743 5744 -1266
		mu 0 3 576 548 575
		f 3 5745 -5745 5746
		mu 0 3 552 575 548
		f 3 -5743 -1262 5747
		mu 0 3 2052 574 573
		f 3 -5740 -5748 -1258
		mu 0 3 572 2052 573
		f 3 5748 -1254 -1260
		mu 0 3 554 570 571
		f 3 5749 5750 -1252
		mu 0 3 570 555 569
		f 3 5751 5752 -5751
		mu 0 3 555 2053 569
		f 3 5753 -5753 5754
		mu 0 3 561 569 2053
		f 3 5755 -5752 5756
		mu 0 3 559 2053 555
		f 3 -1248 -5741 -1256
		mu 0 3 568 567 572
		f 3 -4553 -5742 -1246
		mu 0 3 566 1725 567
		f 3 -4551 -1244 -4544
		mu 0 3 1722 566 565
		f 3 -4535 -4538 -1242
		mu 0 3 563 1206 565
		f 3 -1251 -5754 -1241
		mu 0 3 564 569 561
		f 3 -4533 -4536 -1238
		mu 0 3 562 1207 563
		f 3 -2953 -4534 -1236
		mu 0 3 560 1216 562
		f 3 -1235 -5755 -5756
		mu 0 3 559 561 2053
		f 3 5757 -2956 -1232
		mu 0 3 532 1218 560
		f 3 -5757 -1222 -1231
		mu 0 3 559 555 557
		f 3 -5750 -5749 -1218
		mu 0 3 555 570 554
		f 3 -1217 -1264 -5746
		mu 0 3 552 554 575
		f 3 -1221 -1214 -1225
		mu 0 3 556 553 551
		f 3 -1226 -1210 5758
		mu 0 3 558 551 550
		f 3 5759 -5759 5760
		mu 0 3 536 558 550
		f 3 -5761 5761 5762
		mu 0 3 536 550 542
		f 3 -1213 -5747 -1206
		mu 0 3 549 552 548
		f 3 -1205 -5744 5763
		mu 0 3 547 548 576
		f 3 -1200 -5762 -1208
		mu 0 3 546 542 550
		f 3 -1191 -1199 5764
		mu 0 3 540 541 545
		f 3 5765 -5765 5766
		mu 0 3 2054 540 545
		f 3 -1188 -5766 5767
		mu 0 3 539 540 2054
		f 3 5768 -5768 5769
		mu 0 3 2055 539 2054
		f 3 5770 5771 -5770
		mu 0 3 2054 2056 2055
		f 3 5772 5773 -5772
		mu 0 3 2056 534 2055
		f 3 5774 -5774 5775
		mu 0 3 538 2055 534
		f 3 5776 5777 -5773
		mu 0 3 2056 2057 534
		f 3 5778 5779 -5778
		mu 0 3 2057 527 534
		f 3 5780 -5779 5781
		mu 0 3 2058 527 2057
		f 3 -5782 -5777 5782
		mu 0 3 2058 2057 2056
		f 3 5783 -5783 5784
		mu 0 3 2059 2058 2056
		f 3 5785 -5785 5786
		mu 0 3 2060 2059 2056
		f 3 5787 -5787 5788
		mu 0 3 2061 2060 2056
		f 3 5789 -5786 5790
		mu 0 3 2062 2059 2060
		f 3 -5790 5791 5792
		mu 0 3 2059 2062 2063
		f 3 -5784 -5793 5793
		mu 0 3 2058 2059 2063
		f 3 5794 -5794 5795
		mu 0 3 526 2058 2063
		f 3 5796 5797 -5796
		mu 0 3 2063 2064 526
		f 3 -5798 5798 5799
		mu 0 3 526 2064 2065
		f 3 5800 -5800 5801
		mu 0 3 2066 526 2065
		f 3 -5802 5802 5803
		mu 0 3 2066 2065 521
		f 3 -5803 5804 5805
		mu 0 3 521 2065 513
		f 3 -5771 5806 -5789
		mu 0 3 2056 2054 2061
		f 3 -5775 -1186 -5769
		mu 0 3 2055 538 539
		f 3 -1182 -5763 -1193
		mu 0 3 537 536 542
		f 3 5807 -5760 -1180
		mu 0 3 533 558 536
		f 3 -1178 -1185 -5776
		mu 0 3 534 535 538
		f 3 -1174 -1229 -5808
		mu 0 3 533 532 558
		f 3 -5758 -1172 -2959
		mu 0 3 1218 532 531
		f 3 -1170 -4528 -2963
		mu 0 3 531 529 1221
		f 3 -1168 -1177 -5780
		mu 0 3 527 530 534
		f 3 -4527 -1166 -3002
		mu 0 3 1237 529 528
		f 3 -1164 -3003 -2999
		mu 0 3 528 525 1236
		f 3 -1162 -5781 -5795
		mu 0 3 526 527 2058
		f 3 -1160 -5801 5808
		mu 0 3 522 526 2066
		f 3 -3004 -1158 -3007
		mu 0 3 1235 525 524
		f 3 -3009 -1156 5809
		mu 0 3 1239 524 523
		f 3 -5810 -1154 5810
		mu 0 3 1239 523 520
		f 3 -5809 -5804 -1152
		mu 0 3 522 2066 521
		f 3 -5811 -1148 -4519
		mu 0 3 1239 520 519
		f 3 -4520 -1144 -4511
		mu 0 3 1241 519 518
		f 3 -4513 -1142 5811
		mu 0 3 1721 518 516
		f 3 -5812 -1138 5812
		mu 0 3 1721 516 446
		f 3 -1140 -1147 -1134
		mu 0 3 515 517 514
		f 3 -5806 -1130 -1151
		mu 0 3 521 513 514
		f 3 -1122 5813 5814
		mu 0 3 509 510 2067
		f 3 5815 5816 -5814
		mu 0 3 510 2068 2067
		f 3 5817 5818 -5817
		mu 0 3 2068 504 2067
		f 3 5819 -5815 5820
		mu 0 3 505 509 2067
		f 3 -1133 -1127 -1118
		mu 0 3 507 512 508
		f 3 -1114 -1120 -5820
		mu 0 3 505 506 509
		f 3 -1113 -5821 -5819
		mu 0 3 504 505 2067
		f 3 -1117 -971 -1137
		mu 0 3 507 449 446
		f 3 -1110 5821 -969
		mu 0 3 448 475 447
		f 3 -5813 -965 -4515
		mu 0 3 1721 446 442
		f 3 -4508 -4514 -957
		mu 0 3 440 1720 442
		f 3 -4509 -953 5822
		mu 0 3 1719 440 436
		f 3 -5823 -943 5823
		mu 0 3 1719 436 435
		f 3 -5824 -941 -4503
		mu 0 3 1719 435 434
		f 3 -4501 -939 -3031
		mu 0 3 1249 434 432
		f 3 -937 -948 5824
		mu 0 3 430 433 438
		f 3 -3033 -3032 -935
		mu 0 3 431 1248 432
		f 3 -4493 -4494 -933
		mu 0 3 429 1253 431
		f 3 -5825 -949 -931
		mu 0 3 430 438 428
		f 3 -3056 -4492 -929
		mu 0 3 425 1258 429
		f 3 -927 -952 5825
		mu 0 3 427 428 439
		f 3 -925 5826 5827
		mu 0 3 426 427 2069
		f 3 -923 -5828 5828
		mu 0 3 424 426 2069
		f 3 5829 -5829 5830
		mu 0 3 419 424 2069
		f 3 -3064 -3055 -921
		mu 0 3 423 1259 425
		f 3 -3069 -3065 -917
		mu 0 3 422 1263 423
		f 3 -3152 -3072 -915
		mu 0 3 420 1265 422
		f 3 -914 -920 -5830
		mu 0 3 419 421 424
		f 3 5831 -3153 -911
		mu 0 3 418 413 420
		f 3 -5832 -907 -897
		mu 0 3 413 418 414
		f 3 -3155 -3154 -895
		mu 0 3 411 1300 413
		f 3 5832 -893 -899
		mu 0 3 389 410 412
		f 3 -4472 -891 -3168
		mu 0 3 1304 411 408
		f 3 5833 -886 5834
		mu 0 3 394 406 409
		f 3 -883 -4463 -3172
		mu 0 3 408 407 1307
		f 3 -875 -4461 -881
		mu 0 3 405 404 407
		f 3 -4459 -873 -4464
		mu 0 3 1713 404 403
		f 3 -871 5835 -4465
		mu 0 3 403 401 1326
		f 3 -4444 -5836 -867
		mu 0 3 400 1326 401
		f 3 -4445 -865 -4440
		mu 0 3 1711 400 383
		f 3 5836 -861 -870
		mu 0 3 402 396 399
		f 3 -859 5837 5838
		mu 0 3 398 397 2070
		f 3 -5838 5839 5840
		mu 0 3 2070 397 386
		f 3 5841 -5839 5842
		mu 0 3 384 398 2070
		f 3 -5837 -878 -855
		mu 0 3 396 402 395
		f 3 -880 -5834 -853
		mu 0 3 395 406 394
		f 3 -5835 5843 -851
		mu 0 3 394 409 393
		f 3 -890 -849 -5844
		mu 0 3 409 392 393
		f 3 -847 -889 5844
		mu 0 3 391 392 410
		f 3 5845 -845 -5845
		mu 0 3 410 390 391
		f 3 -5846 -5833 -843
		mu 0 3 390 410 389
		f 3 -841 -901 5846
		mu 0 3 387 389 415
		f 3 -858 -839 -5840
		mu 0 3 397 388 386
		f 3 -5841 -835 -5843
		mu 0 3 2070 386 384
		f 3 5847 -834 5848
		mu 0 3 2071 382 385
		f 3 -5849 5849 5850
		mu 0 3 2071 385 2072
		f 3 -863 -5842 -831
		mu 0 3 383 398 384
		f 3 -4437 -4441 -829
		mu 0 3 379 1710 383
		f 3 -4435 -820 5851
		mu 0 3 1708 379 376
		f 3 -5852 -814 -4431
		mu 0 3 1708 376 375
		f 3 -812 -3234 -4428
		mu 0 3 375 373 1335
		f 3 -816 5852 -810
		mu 0 3 374 377 372
		f 3 -4070 -3238 -808
		mu 0 3 371 1338 373
		f 3 -802 -807 5853
		mu 0 3 369 370 372
		f 3 -4071 -804 -798
		mu 0 3 367 371 368
		f 3 -4040 -4065 -796
		mu 0 3 364 1635 367
		f 3 -790 -4046 -4038
		mu 0 3 364 363 1634
		f 3 5854 -786 5855
		mu 0 3 2073 361 362
		f 3 -5855 5856 -785
		mu 0 3 361 2073 360
		f 3 5857 5858 -782
		mu 0 3 360 2074 352
		f 3 -788 -778 -4045
		mu 0 3 363 359 358
		f 3 -776 -4053 -4044
		mu 0 3 358 357 1636
		f 3 -4649 -774 -2267
		mu 0 3 982 357 355
		f 3 -2268 -770 -2271
		mu 0 3 984 355 354
		f 3 -2272 -768 -2609
		mu 0 3 985 354 350
		f 3 -773 -780 -767
		mu 0 3 353 356 352
		f 3 5859 -764 -5859
		mu 0 3 2074 351 352
		f 3 -2392 -760 5860
		mu 0 3 1028 350 347
		f 3 5861 5862 -759
		mu 0 3 349 2075 348
		f 3 5863 -5862 5864
		mu 0 3 2076 2075 349
		f 3 5865 -5864 5866
		mu 0 3 2077 2075 2076
		f 3 -5866 5867 5868
		mu 0 3 2075 2077 2078
		f 3 5869 -5868 5870
		mu 0 3 2079 2078 2077
		f 3 -5870 5871 5872
		mu 0 3 2078 2079 2080
		f 3 -5872 5873 5874
		mu 0 3 2080 2079 2081
		f 3 -5874 5875 5876
		mu 0 3 2081 2079 2082
		f 3 -5877 5877 5878
		mu 0 3 2081 2082 2083
		f 3 5879 -5879 5880
		mu 0 3 2084 2081 2083
		f 3 -5881 5881 5882
		mu 0 3 2084 2083 2085
		f 3 -5883 5883 5884
		mu 0 3 2084 2085 2086
		f 3 5885 -5884 5886
		mu 0 3 2087 2086 2085
		f 3 -5887 5887 5888
		mu 0 3 2087 2085 2088
		f 3 5889 -5889 5890
		mu 0 3 2089 2087 2088
		f 3 5891 5892 -5891
		mu 0 3 2088 2090 2089
		f 3 -5893 5893 5894
		mu 0 3 2089 2090 2091
		f 3 -5894 5895 5896
		mu 0 3 2091 2090 2092
		f 3 5897 5898 -5897
		mu 0 3 2092 2093 2091
		f 3 -5899 5899 5900
		mu 0 3 2091 2093 2094
		f 3 5901 -5900 5902
		mu 0 3 2095 2094 2093
		f 3 5903 -5902 5904
		mu 0 3 2096 2094 2095
		f 3 5905 -5905 5906
		mu 0 3 2097 2096 2095
		f 3 5907 -5906 5908
		mu 0 3 2098 2096 2097
		f 3 5909 -5909 5910
		mu 0 3 2099 2098 2097
		f 3 5911 5912 -5910
		mu 0 3 2099 2100 2098
		f 3 5913 -5913 5914
		mu 0 3 2101 2098 2100
		f 3 5915 5916 -5915
		mu 0 3 2100 2102 2101
		f 3 5917 5918 -5917
		mu 0 3 2102 2103 2101
		f 3 5919 5920 -5919
		mu 0 3 2103 2104 2101
		f 3 5921 -5921 5922
		mu 0 3 2105 2101 2104
		f 3 5923 -5923 5924
		mu 0 3 2106 2105 2104
		f 3 5925 -5925 5926
		mu 0 3 2107 2106 2104
		f 3 5927 5928 -5926
		mu 0 3 2107 2108 2106
		f 3 5929 5930 -5929
		mu 0 3 2108 2109 2106
		f 3 5931 5932 -5931
		mu 0 3 2109 2110 2106
		f 3 -5932 5933 5934
		mu 0 3 2110 2109 2111
		f 3 5935 -5934 5936
		mu 0 3 2112 2111 2109
		f 3 5937 -5936 5938
		mu 0 3 2113 2111 2112
		f 3 5939 -5938 5940
		mu 0 3 2114 2111 2113
		f 3 -5941 5941 5942
		mu 0 3 2114 2113 2115
		f 3 5943 -5942 5944
		mu 0 3 2116 2115 2113
		f 3 5945 5946 -5945
		mu 0 3 2113 2117 2116
		f 3 5947 5948 -5947
		mu 0 3 2117 2118 2116
		f 3 5949 5950 -5948
		mu 0 3 2117 2119 2118
		f 3 -5951 5951 5952
		mu 0 3 2118 2119 2120
		f 3 5953 -5953 5954
		mu 0 3 2121 2118 2120
		f 3 5955 -5955 5956
		mu 0 3 2122 2121 2120
		f 3 5957 -5957 5958
		mu 0 3 2123 2122 2120
		f 3 5959 -5959 5960
		mu 0 3 2124 2123 2120
		f 3 5961 -5961 5962
		mu 0 3 2125 2124 2120
		f 3 5963 -5963 5964
		mu 0 3 2126 2125 2120
		f 3 5965 -5965 5966
		mu 0 3 2127 2126 2120
		f 3 5967 5968 -5966
		mu 0 3 2127 2128 2126
		f 3 -5969 5969 5970
		mu 0 3 2126 2128 2129
		f 3 5971 -5970 5972
		mu 0 3 2130 2129 2128
		f 3 5973 5974 -5973
		mu 0 3 2128 345 2130
		f 3 5975 -5974 5976
		mu 0 3 2131 345 2128
		f 3 5977 -5976 5978
		mu 0 3 2132 345 2131
		f 3 -5979 5979 5980
		mu 0 3 2132 2131 2133
		f 3 5981 5982 -5980
		mu 0 3 2131 2134 2133
		f 3 -5983 5983 5984
		mu 0 3 2133 2134 2135
		f 3 5985 5986 -5984
		mu 0 3 2134 2136 2135
		f 3 -5987 5987 5988
		mu 0 3 2135 2136 2137
		f 3 5989 -5988 5990
		mu 0 3 2138 2137 2136
		f 3 -5990 5991 5992
		mu 0 3 2137 2138 2139
		f 3 -5993 5993 5994
		mu 0 3 2137 2139 336
		f 3 5995 5996 -5992
		mu 0 3 2138 2140 2139
		f 3 5997 -5997 5998
		mu 0 3 335 2139 2140
		f 3 5999 6000 -5999
		mu 0 3 2140 2141 335
		f 3 6001 6002 -6001
		mu 0 3 2141 2142 335
		f 3 -6002 6003 6004
		mu 0 3 2142 2141 2143
		f 3 -6004 6005 6006
		mu 0 3 2143 2141 2144
		f 3 6007 -6007 6008
		mu 0 3 2145 2143 2144
		f 3 6009 6010 -6009
		mu 0 3 2144 2146 2145
		f 3 6011 -6010 6012
		mu 0 3 2117 2146 2144
		f 3 6013 6014 -6006
		mu 0 3 2141 2119 2144
		f 3 -6014 6015 6016
		mu 0 3 2119 2141 2147
		f 3 6017 -6017 6018
		mu 0 3 2148 2119 2147
		f 3 6019 6020 -6019
		mu 0 3 2147 2138 2148
		f 3 6021 -6021 6022
		mu 0 3 2134 2148 2138
		f 3 -6018 -6022 6023
		mu 0 3 2119 2148 2134
		f 3 -6024 6024 6025
		mu 0 3 2119 2134 2127
		f 3 -6005 6026 6027
		mu 0 3 2142 2143 2149
		f 3 -6028 6028 6029
		mu 0 3 2142 2149 332
		f 3 6030 6031 -6029
		mu 0 3 2149 2150 332
		f 3 6032 -6032 6033
		mu 0 3 2151 332 2150
		f 3 -6016 -6000 6034
		mu 0 3 2147 2141 2140
		f 3 -6035 -5996 -6020
		mu 0 3 2147 2140 2138
		f 3 6035 6036 -5989
		mu 0 3 2137 343 2135
		f 3 6037 6038 -6036
		mu 0 3 2137 338 343
		f 3 -5986 -6023 -5991
		mu 0 3 2136 2134 2138
		f 3 -6025 -5982 6039
		mu 0 3 2127 2134 2131
		f 3 -5985 6040 -5981
		mu 0 3 2133 2135 2132
		f 3 6041 -5978 -6041
		mu 0 3 2135 345 2132
		f 3 6042 6043 -5972
		mu 0 3 2130 346 2129
		f 3 6044 6045 -6044
		mu 0 3 346 2075 2129
		f 3 -5971 6046 6047
		mu 0 3 2126 2129 2078
		f 3 -5977 -5968 -6040
		mu 0 3 2131 2128 2127
		f 3 6048 6049 -5964
		mu 0 3 2126 2084 2125
		f 3 6050 6051 -6049
		mu 0 3 2126 2080 2084
		f 3 6052 6053 -5962
		mu 0 3 2125 2089 2124
		f 3 6054 6055 -5960
		mu 0 3 2124 2091 2123
		f 3 -6056 6056 -5958
		mu 0 3 2123 2091 2122
		f 3 6057 6058 -5956
		mu 0 3 2122 2094 2121
		f 3 6059 -6059 6060
		mu 0 3 2152 2121 2094
		f 3 -6061 6061 6062
		mu 0 3 2152 2094 2153
		f 3 6063 6064 -6062
		mu 0 3 2094 2098 2153
		f 3 -6063 6065 6066
		mu 0 3 2152 2153 2114
		f 3 6067 6068 -6066
		mu 0 3 2153 2110 2114
		f 3 6069 -6068 6070
		mu 0 3 2105 2110 2153
		f 3 -6067 6071 -6060
		mu 0 3 2152 2114 2121
		f 3 -6072 6072 6073
		mu 0 3 2121 2114 2154
		f 3 -6074 6074 -5954
		mu 0 3 2121 2154 2118
		f 3 -6075 6075 6076
		mu 0 3 2118 2154 2115
		f 3 -5967 -5952 -6026
		mu 0 3 2127 2120 2119
		f 3 -6013 -6015 -5950
		mu 0 3 2117 2144 2119
		f 3 6077 -6012 -5946
		mu 0 3 2113 2146 2117
		f 3 -6077 -5944 -5949
		mu 0 3 2118 2115 2116
		f 3 -6073 -5943 -6076
		mu 0 3 2154 2114 2115
		f 3 -6069 -5935 -5940
		mu 0 3 2114 2110 2111
		f 3 -5930 6078 -5937
		mu 0 3 2109 2108 2112
		f 3 6079 6080 -6079
		mu 0 3 2108 2155 2112
		f 3 -6080 -5928 6081
		mu 0 3 2155 2108 2107
		f 3 -6082 6082 6083
		mu 0 3 2155 2107 2156
		f 3 6084 -6083 6085
		mu 0 3 2103 2156 2107
		f 3 -5924 -5933 -6070
		mu 0 3 2105 2106 2110
		f 3 -5922 -6071 6086
		mu 0 3 2101 2105 2153
		f 3 -6086 -5927 -5920
		mu 0 3 2103 2107 2104
		f 3 6087 -5918 6088
		mu 0 3 2157 2103 2102
		f 3 6089 6090 -6089
		mu 0 3 2102 2158 2157
		f 3 6091 -6090 -5916
		mu 0 3 2100 2158 2102
		f 3 -6087 -6065 -5914
		mu 0 3 2101 2153 2098
		f 3 -6092 -5912 6092
		mu 0 3 2158 2100 2099
		f 3 -6064 -5904 -5908
		mu 0 3 2098 2094 2096
		f 3 -6057 -5901 -6058
		mu 0 3 2122 2091 2094
		f 3 -6054 -5895 -6055
		mu 0 3 2124 2089 2091
		f 3 6093 -5892 6094
		mu 0 3 2159 2090 2088
		f 3 6095 -5890 -6053
		mu 0 3 2125 2087 2089
		f 3 6096 -6095 -5888
		mu 0 3 2085 2159 2088
		f 3 6097 6098 -6097
		mu 0 3 2085 2160 2159
		f 3 6099 6100 -6099
		mu 0 3 2160 2161 2159
		f 3 6101 -5886 -6096
		mu 0 3 2125 2086 2087
		f 3 -5885 -6102 -6050
		mu 0 3 2084 2086 2125
		f 3 -5882 6102 -6098
		mu 0 3 2085 2083 2160
		f 3 -6052 -5875 -5880
		mu 0 3 2084 2080 2081
		f 3 -5873 -6051 -6048
		mu 0 3 2078 2080 2126
		f 3 -5869 -6047 -6046
		mu 0 3 2075 2078 2129
		f 3 -757 -5863 -6045
		mu 0 3 346 348 2075
		f 3 6103 -5861 -754
		mu 0 3 342 1028 347
		f 3 -5975 -753 -6043
		mu 0 3 2130 345 346
		f 3 6104 -751 -6042
		mu 0 3 2135 344 345
		f 3 -6037 -749 -6105
		mu 0 3 2135 343 344
		f 3 -2387 -6104 -744
		mu 0 3 340 1028 342
		f 3 -742 -746 -6039
		mu 0 3 338 341 343
		f 3 -740 -2400 -2382
		mu 0 3 340 339 1025
		f 3 -2366 -2369 -738
		mu 0 3 337 1020 339
		f 3 -5995 -737 -6038
		mu 0 3 2137 336 338
		f 3 -5994 -5998 -732
		mu 0 3 336 2139 335
		f 3 -6003 -6030 -730
		mu 0 3 335 2142 332
		f 3 -2402 -734 -728
		mu 0 3 333 337 334
		f 3 -726 6105 -2357
		mu 0 3 333 328 1017
		f 3 6106 -724 -6033
		mu 0 3 2151 331 332
		f 3 6107 -6107 6108
		mu 0 3 2162 331 2151
		f 3 -722 -6108 6109
		mu 0 3 330 331 2162
		f 3 6110 -6110 6111
		mu 0 3 2163 330 2162
		f 3 6112 -6111 6113
		mu 0 3 318 330 2163
		f 3 6114 6115 -6114
		mu 0 3 2163 2164 318
		f 3 6116 6117 -718
		mu 0 3 320 324 329
		f 3 -6106 -714 -2356
		mu 0 3 1017 328 327
		f 3 6118 -2352 -712
		mu 0 3 325 1015 327
		f 3 -710 -716 -6118
		mu 0 3 324 326 329
		f 3 -6119 -708 -2403
		mu 0 3 1015 325 323
		f 3 -2424 -2408 -704
		mu 0 3 322 1031 323
		f 3 6119 -2441 -702
		mu 0 3 319 1042 322
		f 3 -706 -6117 -701
		mu 0 3 321 324 320
		f 3 -721 -6113 -698
		mu 0 3 320 330 318
		f 3 6120 -6120 -696
		mu 0 3 316 1042 319
		f 3 6121 -694 -6116
		mu 0 3 2164 317 318
		f 3 -6122 6122 6123
		mu 0 3 317 2164 2165
		f 3 -6124 6124 6125
		mu 0 3 317 2165 309
		f 3 6126 6127 -6125
		mu 0 3 2165 2166 309
		f 3 6128 6129 -6128
		mu 0 3 2166 2167 309
		f 3 6130 -6130 6131
		mu 0 3 2168 309 2167
		f 3 -6132 6132 6133
		mu 0 3 2168 2167 2169
		f 3 -6134 6134 6135
		mu 0 3 2168 2169 2170
		f 3 6136 6137 -6136
		mu 0 3 2170 2171 2168
		f 3 -6138 6138 6139
		mu 0 3 2168 2171 2172
		f 3 6140 6141 -6139
		mu 0 3 2171 2173 2172
		f 3 6142 6143 -6142
		mu 0 3 2173 2174 2172
		f 3 6144 -6144 6145
		mu 0 3 307 2172 2174
		f 3 -6146 6146 6147
		mu 0 3 307 2174 2175
		f 3 6148 -6147 6149
		mu 0 3 2176 2175 2174
		f 3 -6149 6150 6151
		mu 0 3 2175 2176 2177
		f 3 6152 6153 -6151
		mu 0 3 2176 2178 2177
		f 3 6154 6155 -6154
		mu 0 3 2178 2179 2177
		f 3 -6156 6156 6157
		mu 0 3 2177 2179 2180
		f 3 6158 6159 -6157
		mu 0 3 2179 2181 2180
		f 3 -6160 6160 6161
		mu 0 3 2180 2181 2182
		f 3 -6161 6162 6163
		mu 0 3 2182 2181 2183
		f 3 6164 6165 -6164
		mu 0 3 2183 2184 2182
		f 3 -6166 6166 6167
		mu 0 3 2182 2184 2185
		f 3 -6167 6168 6169
		mu 0 3 2185 2184 2186
		f 3 6170 -6170 6171
		mu 0 3 2187 2185 2186
		f 3 -6172 6172 6173
		mu 0 3 2187 2186 2188
		f 3 -6174 6174 6175
		mu 0 3 2187 2188 2189
		f 3 -6176 6176 6177
		mu 0 3 2187 2189 2190
		f 3 6178 6179 -6178
		mu 0 3 2190 2191 2187
		f 3 -6180 6180 6181
		mu 0 3 2187 2191 2192
		f 3 6182 6183 -6181
		mu 0 3 2191 262 2192
		f 3 6184 6185 -6183
		mu 0 3 2191 252 262
		f 3 -6185 -6179 6186
		mu 0 3 252 2191 2190
		f 3 -6187 6187 6188
		mu 0 3 252 2190 2193
		f 3 6189 -6188 6190
		mu 0 3 2194 2193 2190
		f 3 6191 6192 -6190
		mu 0 3 2194 243 2193
		f 3 6193 -6193 6194
		mu 0 3 250 2193 243
		f 3 6195 -6192 6196
		mu 0 3 2195 243 2194
		f 3 6197 6198 -6197
		mu 0 3 2194 2189 2195
		f 3 6199 -6196 6200
		mu 0 3 225 243 2195
		f 3 6201 -6201 6202
		mu 0 3 2196 225 2195
		f 3 6203 -6203 6204
		mu 0 3 2188 2196 2195
		f 3 6205 6206 -6204
		mu 0 3 2188 2197 2196
		f 3 6207 6208 -6207
		mu 0 3 2197 2198 2196
		f 3 -6209 6209 6210
		mu 0 3 2196 2198 2199
		f 3 6211 -6210 6212
		mu 0 3 2200 2199 2198
		f 3 6213 -6213 6214
		mu 0 3 2201 2200 2198
		f 3 6215 6216 -6215
		mu 0 3 2198 2202 2201
		f 3 -6217 6217 6218
		mu 0 3 2201 2202 2203
		f 3 -6219 6219 6220
		mu 0 3 2201 2203 2204
		f 3 6221 6222 -6221
		mu 0 3 2204 2205 2201
		f 3 6223 6224 -6223
		mu 0 3 2205 2206 2201
		f 3 -6224 6225 6226
		mu 0 3 2206 2205 219
		f 3 6227 -6227 6228
		mu 0 3 223 2206 219
		f 3 6229 -6228 6230
		mu 0 3 2199 2206 223
		f 3 6231 6232 -6226
		mu 0 3 2205 215 219
		f 3 -6222 6233 6234
		mu 0 3 2205 2204 214
		f 3 6235 6236 -6220
		mu 0 3 2203 2207 2204
		f 3 6237 6238 -6237
		mu 0 3 2207 2208 2204
		f 3 -6239 6239 6240
		mu 0 3 2204 2208 213
		f 3 6241 6242 -6240
		mu 0 3 2208 2209 213
		f 3 -6242 6243 6244
		mu 0 3 2209 2208 2210
		f 3 6245 -6244 6246
		mu 0 3 2211 2210 2208
		f 3 6247 -6246 6248
		mu 0 3 2212 2210 2211
		f 3 -6249 6249 6250
		mu 0 3 2212 2211 2213
		f 3 -6250 6251 6252
		mu 0 3 2213 2211 2214
		f 3 -6252 6253 6254
		mu 0 3 2214 2211 2207
		f 3 -6253 6255 6256
		mu 0 3 2213 2214 2181
		f 3 6257 -6251 6258
		mu 0 3 2215 2212 2213
		f 3 -6259 6259 6260
		mu 0 3 2215 2213 2216
		f 3 -6261 6261 6262
		mu 0 3 2215 2216 2217
		f 3 6263 -6263 6264
		mu 0 3 2218 2215 2217
		f 3 6265 -6265 6266
		mu 0 3 2219 2218 2217
		f 3 6267 -6266 6268
		mu 0 3 2220 2218 2219
		f 3 -6269 6269 6270
		mu 0 3 2220 2219 2221
		f 3 6271 6272 -6270
		mu 0 3 2219 2222 2221
		f 3 6273 6274 -6273
		mu 0 3 2222 2173 2221
		f 3 -6274 6275 6276
		mu 0 3 2173 2222 2176
		f 3 6277 6278 -6276
		mu 0 3 2222 2223 2176
		f 3 6279 -6278 -6272
		mu 0 3 2219 2223 2222
		f 3 6280 6281 -6280
		mu 0 3 2219 2216 2223
		f 3 6282 6283 -6282
		mu 0 3 2216 2178 2223
		f 3 6284 -6271 6285
		mu 0 3 2224 2220 2221
		f 3 6286 6287 -6286
		mu 0 3 2221 2225 2224
		f 3 6288 -6288 6289
		mu 0 3 2226 2224 2225
		f 3 6290 -6290 6291
		mu 0 3 2227 2226 2225
		f 3 6292 6293 -6292
		mu 0 3 2225 2228 2227
		f 3 -6294 6294 6295
		mu 0 3 2227 2228 2229
		f 3 6296 6297 -6295
		mu 0 3 2228 2230 2229
		f 3 6298 6299 -6298
		mu 0 3 2230 2231 2229
		f 3 6300 -6300 6301
		mu 0 3 2232 2229 2231
		f 3 -6302 6302 6303
		mu 0 3 2232 2231 2233
		f 3 -6303 6304 6305
		mu 0 3 2233 2231 2234
		f 3 6306 6307 -6306
		mu 0 3 2234 2235 2233
		f 3 6308 6309 -6308
		mu 0 3 2235 2236 2233
		f 3 -6310 6310 6311
		mu 0 3 2233 2236 2237
		f 3 -6311 6312 6313
		mu 0 3 2237 2236 2238
		f 3 6314 6315 -6314
		mu 0 3 2238 2239 2237
		f 3 -6316 6316 6317
		mu 0 3 2237 2239 2232
		f 3 -6317 6318 6319
		mu 0 3 2232 2239 2240
		f 3 -6319 6320 6321
		mu 0 3 2240 2239 2241
		f 3 6322 6323 -6322
		mu 0 3 2241 2242 2240
		f 3 6324 6325 -6324
		mu 0 3 2242 2226 2240
		f 3 6326 -6325 6327
		mu 0 3 2243 2226 2242
		f 3 6328 -6328 6329
		mu 0 3 2244 2243 2242
		f 3 6330 -6329 6331
		mu 0 3 2245 2243 2244
		f 3 6332 -6332 6333
		mu 0 3 2246 2245 2244
		f 3 -6334 6334 6335
		mu 0 3 2246 2244 2241;
	setAttr ".fc[4000:4499]"
		f 3 6336 -6336 6337
		mu 0 3 2238 2246 2241
		f 3 6338 6339 -6337
		mu 0 3 2238 2247 2246
		f 3 6340 -6339 6341
		mu 0 3 2248 2247 2238
		f 3 6342 6343 -6342
		mu 0 3 2238 2249 2248
		f 3 -6344 6344 6345
		mu 0 3 2248 2249 2250
		f 3 6346 -6346 6347
		mu 0 3 2251 2248 2250
		f 3 6348 -6348 6349
		mu 0 3 2252 2251 2250
		f 3 -6350 6350 6351
		mu 0 3 2252 2250 2253
		f 3 -6352 6352 6353
		mu 0 3 2252 2253 2254
		f 3 -6354 6354 6355
		mu 0 3 2252 2254 2255
		f 3 6356 6357 -6355
		mu 0 3 2254 2256 2255
		f 3 6358 -6358 6359
		mu 0 3 2257 2255 2256
		f 3 -6360 6360 6361
		mu 0 3 2257 2256 2258
		f 3 6362 6363 -6362
		mu 0 3 2258 2259 2257
		f 3 6364 6365 -6364
		mu 0 3 2259 2260 2257
		f 3 -6366 6366 6367
		mu 0 3 2257 2260 2261
		f 3 6368 -6367 6369
		mu 0 3 2262 2261 2260
		f 3 6370 -6370 6371
		mu 0 3 2263 2262 2260
		f 3 6372 -6371 6373
		mu 0 3 2264 2262 2263
		f 3 6374 -6374 6375
		mu 0 3 2265 2264 2263
		f 3 -6376 6376 6377
		mu 0 3 2265 2263 138
		f 3 6378 6379 -6377
		mu 0 3 2263 2266 138
		f 3 -6379 6380 6381
		mu 0 3 2266 2263 2259
		f 3 -6382 6382 6383
		mu 0 3 2266 2259 2267
		f 3 -6384 6384 6385
		mu 0 3 2266 2267 135
		f 3 6386 6387 -6385
		mu 0 3 2267 2268 135
		f 3 -6387 6388 6389
		mu 0 3 2268 2267 2269
		f 3 6390 6391 -6390
		mu 0 3 2269 113 2268
		f 3 6392 -6389 6393
		mu 0 3 2270 2269 2267
		f 3 6394 6395 -6394
		mu 0 3 2267 2258 2270
		f 3 6396 6397 -6396
		mu 0 3 2258 2271 2270
		f 3 6398 -6398 6399
		mu 0 3 2272 2270 2271
		f 3 6400 -6400 6401
		mu 0 3 2235 2272 2271
		f 3 6402 -6402 6403
		mu 0 3 2253 2235 2271
		f 3 6404 6405 -6404
		mu 0 3 2271 2256 2253
		f 3 -6403 6406 6407
		mu 0 3 2235 2253 2249
		f 3 -6399 6408 6409
		mu 0 3 2270 2272 2273
		f 3 6410 6411 -6410
		mu 0 3 2273 112 2270
		f 3 6412 6413 -6411
		mu 0 3 2273 2274 112
		f 3 6414 6415 -6414
		mu 0 3 2274 2275 112
		f 3 6416 6417 -6415
		mu 0 3 2274 94 2275
		f 3 -6418 6418 6419
		mu 0 3 2275 94 100
		f 3 6420 6421 -6420
		mu 0 3 100 109 2275
		f 3 -6413 6422 6423
		mu 0 3 2274 2273 2276
		f 3 6424 6425 -6423
		mu 0 3 2273 2277 2276
		f 3 -6426 6426 6427
		mu 0 3 2276 2277 2278
		f 3 6428 6429 -6427
		mu 0 3 2277 2279 2278
		f 3 6430 -6430 6431
		mu 0 3 2280 2278 2279
		f 3 -6432 6432 6433
		mu 0 3 2280 2279 2281
		f 3 6434 -6433 6435
		mu 0 3 2231 2281 2279
		f 3 -6434 6436 6437
		mu 0 3 2280 2281 2282
		f 3 -6438 6438 6439
		mu 0 3 2280 2282 2283
		f 3 6440 6441 -6437
		mu 0 3 2281 2230 2282
		f 3 6442 -6442 6443
		mu 0 3 2284 2282 2230
		f 3 6444 6445 -6444
		mu 0 3 2230 2285 2284
		f 3 6446 -6445 6447
		mu 0 3 2286 2285 2230
		f 3 6448 6449 -6447
		mu 0 3 2286 2287 2285
		f 3 6450 6451 -6449
		mu 0 3 2286 2288 2287
		f 3 6452 6453 -6451
		mu 0 3 2286 2170 2288
		f 3 6454 -6453 6455
		mu 0 3 2228 2170 2286
		f 3 6456 -6431 -6440
		mu 0 3 2283 2278 2280
		f 3 -6457 6457 6458
		mu 0 3 2278 2283 2289
		f 3 -6459 6459 6460
		mu 0 3 2278 2289 2290
		f 3 6461 -6460 6462
		mu 0 3 2291 2290 2289
		f 3 6463 -6462 6464
		mu 0 3 2292 2290 2291
		f 3 -6465 6465 6466
		mu 0 3 2292 2291 2293
		f 3 6467 6468 -6467
		mu 0 3 2293 2294 2292
		f 3 6469 -6469 6470
		mu 0 3 2295 2292 2294
		f 3 6471 -6471 6472
		mu 0 3 2296 2295 2294
		f 3 6473 6474 -6472
		mu 0 3 2296 87 2295
		f 3 6475 -6475 6476
		mu 0 3 2297 2295 87
		f 3 6477 6478 -6476
		mu 0 3 2297 2290 2295
		f 3 6479 -6478 6480
		mu 0 3 2276 2290 2297
		f 3 6481 -6473 -6468
		mu 0 3 2293 2296 2294
		f 3 6482 6483 -6482
		mu 0 3 2293 2298 2296
		f 3 6484 6485 -6484
		mu 0 3 2298 86 2296
		f 3 6486 6487 -6485
		mu 0 3 2298 84 86
		f 3 -6487 6488 6489
		mu 0 3 84 2298 2299
		f 3 6490 6491 -6490
		mu 0 3 2299 2300 84
		f 3 6492 -6489 -6483
		mu 0 3 2293 2299 2298
		f 3 -6493 -6466 6493
		mu 0 3 2299 2293 2291
		f 3 -6479 -6464 -6470
		mu 0 3 2295 2290 2292
		f 3 6494 -6436 -6429
		mu 0 3 2277 2231 2279
		f 3 -6428 -6461 -6480
		mu 0 3 2276 2278 2290
		f 3 6495 -6424 -6481
		mu 0 3 2297 2274 2276
		f 3 -6496 6496 6497
		mu 0 3 2274 2297 91
		f 3 6498 -6425 -6409
		mu 0 3 2272 2277 2273
		f 3 -6499 6499 6500
		mu 0 3 2277 2272 2234
		f 3 -6393 -6412 6501
		mu 0 3 2269 2270 112
		f 3 6502 -6375 6503
		mu 0 3 2301 2264 2265
		f 3 -6504 6504 6505
		mu 0 3 2301 2265 147
		f 3 6506 -6506 6507
		mu 0 3 2302 2301 147
		f 3 -6507 6508 6509
		mu 0 3 2301 2302 2303
		f 3 6510 6511 -6509
		mu 0 3 2302 2304 2303
		f 3 -6512 6512 6513
		mu 0 3 2303 2304 2305
		f 3 -6513 6514 6515
		mu 0 3 2305 2304 2306
		f 3 -6515 6516 6517
		mu 0 3 2306 2304 2307
		f 3 6518 -6518 6519
		mu 0 3 2308 2306 2307
		f 3 6520 6521 -6520
		mu 0 3 2307 2309 2308
		f 3 6522 -6522 6523
		mu 0 3 2310 2308 2309
		f 3 -6524 6524 6525
		mu 0 3 2310 2309 2311
		f 3 -6526 6526 6527
		mu 0 3 2310 2311 2312
		f 3 -6528 6528 6529
		mu 0 3 2310 2312 2313
		f 3 -6529 6530 6531
		mu 0 3 2313 2312 2314
		f 3 6532 6533 -6532
		mu 0 3 2314 2315 2313
		f 3 6534 -6534 6535
		mu 0 3 2316 2313 2315
		f 3 6536 6537 -6536
		mu 0 3 2315 2317 2316
		f 3 6538 6539 -6538
		mu 0 3 2317 2318 2316
		f 3 6540 6541 -6540
		mu 0 3 2318 2308 2316
		f 3 6542 -6539 6543
		mu 0 3 2319 2318 2317
		f 3 6544 -6544 6545
		mu 0 3 2320 2319 2317
		f 3 6546 6547 -6546
		mu 0 3 2317 2321 2320
		f 3 6548 -6548 6549
		mu 0 3 2261 2320 2321
		f 3 -6550 6550 6551
		mu 0 3 2261 2321 2255
		f 3 6552 6553 -6551
		mu 0 3 2321 2322 2255
		f 3 6554 -6553 -6547
		mu 0 3 2317 2322 2321
		f 3 -6545 6555 6556
		mu 0 3 2319 2320 2262
		f 3 6557 -6543 6558
		mu 0 3 2305 2318 2319
		f 3 6559 -6555 -6537
		mu 0 3 2315 2322 2317
		f 3 -6560 6560 6561
		mu 0 3 2322 2315 2252
		f 3 -6561 6562 6563
		mu 0 3 2252 2315 2323
		f 3 -6535 -6542 6564
		mu 0 3 2313 2316 2308
		f 3 -6533 6565 -6563
		mu 0 3 2315 2314 2323
		f 3 -6566 6566 6567
		mu 0 3 2323 2314 2324
		f 3 -6568 6568 6569
		mu 0 3 2323 2324 2245
		f 3 -6570 6570 6571
		mu 0 3 2323 2245 2247
		f 3 6572 -6572 6573
		mu 0 3 2325 2323 2247
		f 3 -6573 6574 6575
		mu 0 3 2323 2325 2251
		f 3 -6567 6576 6577
		mu 0 3 2324 2314 2326
		f 3 6578 6579 -6578
		mu 0 3 2326 2327 2324
		f 3 -6580 6580 6581
		mu 0 3 2324 2327 2243
		f 3 6582 6583 -6581
		mu 0 3 2327 2328 2243
		f 3 6584 6585 -6584
		mu 0 3 2328 2329 2243
		f 3 6586 -6585 6587
		mu 0 3 2330 2329 2328
		f 3 6588 6589 -6587
		mu 0 3 2330 2220 2329
		f 3 6590 -6589 6591
		mu 0 3 2331 2220 2330
		f 3 6592 6593 -6592
		mu 0 3 2330 2332 2331
		f 3 6594 6595 -6594
		mu 0 3 2332 2333 2331
		f 3 -6596 6596 6597
		mu 0 3 2331 2333 2334
		f 3 -6598 6598 6599
		mu 0 3 2331 2334 2335
		f 3 -6599 6600 6601
		mu 0 3 2335 2334 2336
		f 3 -6601 6602 6603
		mu 0 3 2336 2334 2337
		f 3 6604 -6604 6605
		mu 0 3 2209 2336 2337
		f 3 -6606 6606 6607
		mu 0 3 2209 2337 2338
		f 3 6608 6609 -6607
		mu 0 3 2337 2339 2338
		f 3 -6610 6610 6611
		mu 0 3 2338 2339 2340
		f 3 -6612 6612 6613
		mu 0 3 2338 2340 2341
		f 3 6614 6615 -6613
		mu 0 3 2340 2342 2341
		f 3 -6616 6616 6617
		mu 0 3 2341 2342 2343
		f 3 -6618 6618 6619
		mu 0 3 2341 2343 2344
		f 3 6620 -6619 6621
		mu 0 3 2345 2344 2343
		f 3 6622 -6622 6623
		mu 0 3 2346 2345 2343
		f 3 6624 -6623 6625
		mu 0 3 2347 2345 2346
		f 3 6626 6627 -6626
		mu 0 3 2346 2348 2347
		f 3 -6628 6628 6629
		mu 0 3 2347 2348 2349
		f 3 6630 6631 -6629
		mu 0 3 2348 2350 2349
		f 3 -6632 6632 6633
		mu 0 3 2349 2350 212
		f 3 -6634 6634 6635
		mu 0 3 2349 212 2351
		f 3 6636 6637 -6635
		mu 0 3 212 2352 2351
		f 3 6638 -6638 6639
		mu 0 3 2353 2351 2352
		f 3 6640 6641 -6640
		mu 0 3 2352 2345 2353
		f 3 6642 -6639 6643
		mu 0 3 2347 2351 2353
		f 3 -6637 6644 6645
		mu 0 3 2352 212 2209
		f 3 6646 6647 -6646
		mu 0 3 2209 2344 2352
		f 3 6648 6649 -6631
		mu 0 3 2348 2354 2350
		f 3 6650 6651 -6650
		mu 0 3 2354 2355 2350
		f 3 -6652 6652 6653
		mu 0 3 2350 2355 2356
		f 3 6654 6655 -6654
		mu 0 3 2356 211 2350
		f 3 -6653 6656 6657
		mu 0 3 2356 2355 2357
		f 3 6658 6659 -6657
		mu 0 3 2355 2358 2357
		f 3 6660 -6660 6661
		mu 0 3 179 2357 2358
		f 3 6662 -6662 6663
		mu 0 3 2359 179 2358
		f 3 6664 -6664 6665
		mu 0 3 2360 2359 2358
		f 3 6666 -6666 6667
		mu 0 3 2354 2360 2358
		f 3 6668 6669 -6667
		mu 0 3 2354 2361 2360
		f 3 6670 6671 -6670
		mu 0 3 2361 2362 2360
		f 3 6672 6673 -6672
		mu 0 3 2362 2363 2360
		f 3 6674 6675 -6673
		mu 0 3 2362 162 2363
		f 3 -6676 6676 6677
		mu 0 3 2363 162 2364
		f 3 -6677 6678 6679
		mu 0 3 2364 162 169
		f 3 6680 6681 -6680
		mu 0 3 169 174 2364
		f 3 -6678 6682 6683
		mu 0 3 2363 2364 2359
		f 3 6684 -6671 6685
		mu 0 3 2365 2362 2361
		f 3 6686 6687 -6685
		mu 0 3 2365 2366 2362
		f 3 6688 -6688 6689
		mu 0 3 2367 2362 2366
		f 3 6690 -6690 6691
		mu 0 3 2368 2367 2366
		f 3 6692 -6692 6693
		mu 0 3 2369 2368 2366
		f 3 6694 6695 -6693
		mu 0 3 2369 2370 2368
		f 3 6696 6697 -6696
		mu 0 3 2370 2371 2368
		f 3 6698 -6697 6699
		mu 0 3 2372 2371 2370
		f 3 6700 6701 -6700
		mu 0 3 2370 2373 2372
		f 3 6702 -6702 6703
		mu 0 3 159 2372 2373
		f 3 -6704 6704 6705
		mu 0 3 159 2373 2374
		f 3 6706 6707 -6706
		mu 0 3 2374 2375 159
		f 3 6708 -6708 6709
		mu 0 3 2376 159 2375
		f 3 6710 -6710 6711
		mu 0 3 2377 2376 2375
		f 3 6712 -6711 6713
		mu 0 3 2378 2376 2377
		f 3 -6714 6714 6715
		mu 0 3 2378 2377 2379
		f 3 6716 -6716 6717
		mu 0 3 2380 2378 2379
		f 3 6718 -6718 6719
		mu 0 3 2309 2380 2379
		f 3 6720 6721 -6720
		mu 0 3 2379 2381 2309
		f 3 6722 -6722 6723
		mu 0 3 2382 2309 2381
		f 3 6724 -6724 6725
		mu 0 3 2383 2382 2381
		f 3 -6726 6726 6727
		mu 0 3 2383 2381 2384
		f 3 6728 -6728 6729
		mu 0 3 2385 2383 2384
		f 3 -6730 6730 6731
		mu 0 3 2385 2384 2386
		f 3 -6731 6732 6733
		mu 0 3 2386 2384 2373
		f 3 -6732 6734 6735
		mu 0 3 2385 2386 2369
		f 3 -6736 6736 6737
		mu 0 3 2385 2369 2365
		f 3 6738 -6738 6739
		mu 0 3 2387 2385 2365
		f 3 6740 -6740 6741
		mu 0 3 2354 2387 2365
		f 3 6742 -6729 -6739
		mu 0 3 2387 2383 2385
		f 3 -6727 6743 6744
		mu 0 3 2384 2381 2374
		f 3 6745 6746 -6744
		mu 0 3 2381 2377 2374
		f 3 6747 -6725 -6743
		mu 0 3 2387 2382 2383
		f 3 6748 6749 -6748
		mu 0 3 2387 2311 2382
		f 3 6750 -6749 6751
		mu 0 3 2388 2311 2387
		f 3 6752 -6752 6753
		mu 0 3 2389 2388 2387
		f 3 6754 -6754 6755
		mu 0 3 2390 2389 2387
		f 3 -6756 6756 6757
		mu 0 3 2390 2387 2342
		f 3 6758 -6757 6759
		mu 0 3 2348 2342 2387
		f 3 -6755 6760 6761
		mu 0 3 2389 2390 2333
		f 3 -6762 6762 6763
		mu 0 3 2389 2333 2391
		f 3 6764 -6764 6765
		mu 0 3 2312 2389 2391
		f 3 -6766 6766 6767
		mu 0 3 2312 2391 2326
		f 3 -6767 6768 6769
		mu 0 3 2326 2391 2332
		f 3 -6770 6770 6771
		mu 0 3 2326 2332 2392
		f 3 -6761 6772 6773
		mu 0 3 2333 2390 2337
		f 3 6774 -6753 -6765
		mu 0 3 2312 2388 2389
		f 3 6775 -6717 6776
		mu 0 3 2393 2378 2380
		f 3 -6777 6777 6778
		mu 0 3 2393 2380 2307
		f 3 6779 -6776 6780
		mu 0 3 2394 2378 2393
		f 3 6781 -6781 6782
		mu 0 3 2302 2394 2393
		f 3 6783 -6782 6784
		mu 0 3 154 2394 2302
		f 3 6785 6786 -6785
		mu 0 3 2302 149 154
		f 3 -6780 6787 6788
		mu 0 3 2378 2394 157
		f 3 -6715 -6746 -6721
		mu 0 3 2379 2377 2381
		f 3 -6789 6789 -6713
		mu 0 3 2378 157 2376
		f 3 -6712 -6707 -6747
		mu 0 3 2377 2375 2374
		f 3 -6745 -6705 -6733
		mu 0 3 2384 2374 2373
		f 3 6790 6791 -6703
		mu 0 3 159 2395 2372
		f 3 -6734 -6701 6792
		mu 0 3 2386 2373 2370
		f 3 6793 -6699 -6792
		mu 0 3 2395 2371 2372
		f 3 6794 6795 -6794
		mu 0 3 2395 2367 2371
		f 3 6796 -6795 6797
		mu 0 3 161 2367 2395
		f 3 -6793 -6695 -6735
		mu 0 3 2386 2370 2369
		f 3 -6796 -6691 -6698
		mu 0 3 2371 2367 2368
		f 3 -6797 6798 -6689
		mu 0 3 2367 161 2362
		f 3 -6737 -6694 -6687
		mu 0 3 2365 2369 2366
		f 3 -6742 -6686 -6669
		mu 0 3 2354 2365 2361
		f 3 -6674 -6684 -6665
		mu 0 3 2360 2363 2359
		f 3 -6683 6799 -6663
		mu 0 3 2359 2364 179
		f 3 6800 6801 -6658
		mu 0 3 2357 208 2356
		f 3 -6668 -6659 -6651
		mu 0 3 2354 2358 2355
		f 3 -6741 -6649 -6760
		mu 0 3 2387 2354 2348
		f 3 -6636 -6643 -6630
		mu 0 3 2349 2351 2347
		f 3 -6627 6802 -6759
		mu 0 3 2348 2346 2342
		f 3 -6644 -6642 -6625
		mu 0 3 2347 2353 2345
		f 3 -6648 -6621 -6641
		mu 0 3 2352 2344 2345
		f 3 -6803 -6624 -6617
		mu 0 3 2342 2346 2343
		f 3 6803 -6758 -6615
		mu 0 3 2340 2390 2342
		f 3 -6614 -6620 6804
		mu 0 3 2338 2341 2344
		f 3 6805 -6804 -6611
		mu 0 3 2339 2390 2340
		f 3 -6609 -6773 -6806
		mu 0 3 2339 2337 2390
		f 3 -6608 -6805 -6647
		mu 0 3 2209 2338 2344
		f 3 6806 -6602 6807
		mu 0 3 2210 2335 2336
		f 3 6808 6809 -6807
		mu 0 3 2210 2396 2335
		f 3 -6600 -6810 6810
		mu 0 3 2331 2335 2396
		f 3 -6597 -6774 -6603
		mu 0 3 2334 2333 2337
		f 3 -6763 -6595 -6769
		mu 0 3 2391 2333 2332
		f 3 6811 -6771 -6593
		mu 0 3 2330 2392 2332
		f 3 -6812 6812 6813
		mu 0 3 2392 2330 2327
		f 3 -6811 6814 -6591
		mu 0 3 2331 2396 2220
		f 3 -6813 -6588 -6583
		mu 0 3 2327 2330 2328
		f 3 -6772 -6814 -6579
		mu 0 3 2326 2392 2327
		f 3 -6531 -6768 -6577
		mu 0 3 2314 2312 2326
		f 3 -6527 -6751 -6775
		mu 0 3 2312 2311 2388
		f 3 -6525 -6723 -6750
		mu 0 3 2311 2309 2382
		f 3 -6530 -6565 -6523
		mu 0 3 2310 2313 2308
		f 3 -6719 -6521 -6778
		mu 0 3 2380 2309 2307
		f 3 6815 -6519 -6541
		mu 0 3 2318 2306 2308
		f 3 6816 -6779 -6517
		mu 0 3 2304 2393 2307
		f 3 -6516 -6816 -6558
		mu 0 3 2305 2306 2318
		f 3 -6514 -6559 6817
		mu 0 3 2303 2305 2319
		f 3 -6818 6818 6819
		mu 0 3 2303 2319 2264
		f 3 -6511 -6783 -6817
		mu 0 3 2304 2302 2393
		f 3 -6510 -6820 -6503
		mu 0 3 2301 2303 2264
		f 3 -6557 -6373 -6819
		mu 0 3 2319 2262 2264
		f 3 -6556 -6549 -6369
		mu 0 3 2262 2320 2261
		f 3 -6365 -6381 -6372
		mu 0 3 2260 2259 2263
		f 3 -6383 -6363 -6395
		mu 0 3 2267 2259 2258
		f 3 -6361 -6405 -6397
		mu 0 3 2258 2256 2271
		f 3 -6368 -6552 -6359
		mu 0 3 2257 2261 2255
		f 3 -6562 -6356 -6554
		mu 0 3 2322 2252 2255
		f 3 -6353 -6406 -6357
		mu 0 3 2254 2253 2256
		f 3 -6564 -6576 -6349
		mu 0 3 2252 2323 2251
		f 3 -6575 6820 -6347
		mu 0 3 2251 2325 2248
		f 3 -6345 -6407 -6351
		mu 0 3 2250 2249 2253
		f 3 -6574 -6341 -6821
		mu 0 3 2325 2247 2248
		f 3 -6571 -6333 -6340
		mu 0 3 2247 2245 2246
		f 3 -6582 -6331 -6569
		mu 0 3 2324 2243 2245
		f 3 -6586 6821 -6327
		mu 0 3 2243 2329 2226
		f 3 -6335 -6330 -6323
		mu 0 3 2241 2244 2242
		f 3 6822 -6320 6823
		mu 0 3 2227 2232 2240
		f 3 -6338 -6321 -6315
		mu 0 3 2238 2241 2239
		f 3 -6313 6824 -6343
		mu 0 3 2238 2236 2249
		f 3 -6825 -6309 -6408
		mu 0 3 2249 2236 2235
		f 3 -6401 -6307 -6500
		mu 0 3 2272 2235 2234
		f 3 -6495 -6501 -6305
		mu 0 3 2231 2277 2234
		f 3 -6304 -6312 -6318
		mu 0 3 2232 2233 2237
		f 3 -6435 -6299 -6441
		mu 0 3 2281 2231 2230
		f 3 -6456 -6448 -6297
		mu 0 3 2228 2286 2230
		f 3 -6823 -6296 -6301
		mu 0 3 2232 2227 2229
		f 3 6825 -6455 -6293
		mu 0 3 2225 2170 2228
		f 3 -6326 -6291 -6824
		mu 0 3 2240 2226 2227
		f 3 6826 -6289 -6822
		mu 0 3 2329 2224 2226
		f 3 -6287 6827 6828
		mu 0 3 2225 2221 2171
		f 3 -6285 -6827 -6590
		mu 0 3 2220 2224 2329
		f 3 6829 -6268 -6815
		mu 0 3 2396 2218 2220
		f 3 6830 6831 -6830
		mu 0 3 2396 2212 2218
		f 3 -6262 -6281 -6267
		mu 0 3 2217 2216 2219
		f 3 6832 6833 -6260
		mu 0 3 2213 2179 2216
		f 3 -6832 -6258 -6264
		mu 0 3 2218 2212 2215
		f 3 -6809 -6248 -6831
		mu 0 3 2396 2210 2212
		f 3 -6605 -6245 -6808
		mu 0 3 2336 2209 2210
		f 3 -6247 -6238 -6254
		mu 0 3 2211 2208 2207
		f 3 -6236 6834 -6255
		mu 0 3 2207 2203 2214
		f 3 6835 -6835 -6218
		mu 0 3 2202 2214 2203
		f 3 6836 6837 -6836
		mu 0 3 2202 2183 2214
		f 3 6838 6839 -6837
		mu 0 3 2202 2197 2183
		f 3 -6225 6840 -6214
		mu 0 3 2201 2206 2200
		f 3 -6841 -6230 -6212
		mu 0 3 2200 2206 2199
		f 3 -6208 -6839 -6216
		mu 0 3 2198 2197 2202
		f 3 6841 6842 -6206
		mu 0 3 2188 2184 2197
		f 3 -6211 6843 -6202
		mu 0 3 2196 2199 225
		f 3 -6177 -6198 -6191
		mu 0 3 2190 2189 2194
		f 3 -6205 -6199 -6175
		mu 0 3 2188 2195 2189
		f 3 -6171 -6182 6844
		mu 0 3 2185 2187 2192
		f 3 6845 -6845 6846
		mu 0 3 2180 2185 2192
		f 3 -6169 -6842 -6173
		mu 0 3 2186 2184 2188
		f 3 -6165 -6840 -6843
		mu 0 3 2184 2183 2197
		f 3 -6256 -6838 -6163
		mu 0 3 2181 2214 2183
		f 3 -6162 -6168 -6846
		mu 0 3 2180 2182 2185
		f 3 -6257 -6159 -6833
		mu 0 3 2213 2181 2179
		f 3 6847 -6158 -6847
		mu 0 3 2192 2177 2180
		f 3 6848 6849 -6848
		mu 0 3 2192 294 2177
		f 3 6850 6851 -6849
		mu 0 3 2192 263 294
		f 3 -6283 -6834 -6155
		mu 0 3 2178 2216 2179
		f 3 -6284 -6153 -6279
		mu 0 3 2223 2178 2176
		f 3 -6152 6852 6853
		mu 0 3 2175 2177 304
		f 3 6854 6855 -6853
		mu 0 3 2177 295 304
		f 3 -6277 -6150 -6143
		mu 0 3 2173 2176 2174
		f 3 -6275 -6141 -6828
		mu 0 3 2221 2173 2171
		f 3 -6145 6856 -6140
		mu 0 3 2172 307 2168
		f 3 -6829 -6137 -6826
		mu 0 3 2225 2171 2170
		f 3 -6454 -6135 6857
		mu 0 3 2288 2170 2169
		f 3 -690 -2444 -6121
		mu 0 3 316 315 1042
		f 3 -2434 -2443 -688
		mu 0 3 313 1041 315
		f 3 -686 -692 6858
		mu 0 3 311 314 317
		f 3 -684 -2437 -2433
		mu 0 3 313 312 1040
		f 3 6859 6860 -682
		mu 0 3 310 285 312
		f 3 6861 6862 -6860
		mu 0 3 310 2397 285
		f 3 6863 6864 -6863
		mu 0 3 2397 299 285
		f 3 -681 -6859 -6126
		mu 0 3 309 311 317
		f 3 6865 -6862 -678
		mu 0 3 308 2397 310
		f 3 -6857 -676 -6131
		mu 0 3 2168 307 309
		f 3 -674 6866 -6866
		mu 0 3 308 306 2397
		f 3 6867 6868 -6867
		mu 0 3 306 302 2397
		f 3 -6148 6869 -672
		mu 0 3 307 2175 305
		f 3 -6870 -6854 -668
		mu 0 3 305 2175 304
		f 3 -670 -664 -6868
		mu 0 3 306 303 302
		f 3 -662 6870 -6869
		mu 0 3 302 300 2397
		f 3 6871 -660 -666
		mu 0 3 304 297 301
		f 3 -6871 -658 -6864
		mu 0 3 2397 300 299
		f 3 6872 -656 -652
		mu 0 3 296 289 298
		f 3 -651 -6872 -6856
		mu 0 3 295 297 304
		f 3 -647 -6855 -6850
		mu 0 3 294 295 2177
		f 3 6873 -644 -6852
		mu 0 3 263 293 294
		f 3 6874 6875 -6874
		mu 0 3 263 269 293
		f 3 6876 -642 6877
		mu 0 3 272 291 293
		f 3 6878 -648 -640
		mu 0 3 290 296 292
		f 3 -6873 -6879 -634
		mu 0 3 289 296 290
		f 3 -657 -632 6879
		mu 0 3 299 289 287
		f 3 6880 6881 -630
		mu 0 3 288 275 284
		f 3 6882 -6880 -628
		mu 0 3 286 299 287
		f 3 -6883 -626 -6865
		mu 0 3 299 286 285
		f 3 -624 -2438 -6861
		mu 0 3 285 283 312
		f 3 -2446 -2439 -618
		mu 0 3 281 1037 283
		f 3 -2600 -2447 -614
		mu 0 3 280 1043 281
		f 3 -612 -2570 -2599
		mu 0 3 280 279 1080
		f 3 6883 -2566 -610
		mu 0 3 277 1079 279
		f 3 6884 6885 -6884
		mu 0 3 277 2398 1079
		f 3 6886 -6886 6887
		mu 0 3 2399 1079 2398
		f 3 -6888 6888 6889
		mu 0 3 2399 2398 257
		f 3 -6889 6890 6891
		mu 0 3 257 2398 2400
		f 3 6892 6893 -6891
		mu 0 3 2398 268 2400
		f 3 6894 6895 -6893
		mu 0 3 2398 273 268
		f 3 -6892 6896 6897
		mu 0 3 257 2400 267
		f 3 6898 6899 -6887
		mu 0 3 2399 255 1079
		f 3 -623 -609 -617
		mu 0 3 282 276 278
		f 3 -6895 -6885 -606
		mu 0 3 273 2398 277
		f 3 -6882 -604 -622
		mu 0 3 284 275 276
		f 3 -6881 -638 -602
		mu 0 3 275 288 274
		f 3 -639 -6877 -600
		mu 0 3 274 291 272
		f 3 6900 -596 -6878
		mu 0 3 293 270 272
		f 3 -6896 -599 -594
		mu 0 3 268 273 271
		f 3 -6876 -593 -6901
		mu 0 3 293 269 270
		f 3 6901 -590 -6875
		mu 0 3 263 266 269
		f 3 -6894 -588 -6897
		mu 0 3 2400 268 267
		f 3 -583 -6902 -578
		mu 0 3 264 266 263
		f 3 -6184 -577 -6851
		mu 0 3 2192 262 263
		f 3 -580 -572 6902
		mu 0 3 265 261 260
		f 3 -6903 -568 -586
		mu 0 3 265 260 258
		f 3 -587 -564 -6898
		mu 0 3 267 258 257
		f 3 -6899 -6890 -562
		mu 0 3 255 2399 257
		f 3 -571 -560 -567
		mu 0 3 259 254 256
		f 3 -558 -2567 -6900
		mu 0 3 255 253 1079
		f 3 -574 -6186 -557
		mu 0 3 254 262 252
		f 3 6903 -2561 -554
		mu 0 3 251 1078 253
		f 3 -553 -6189 -6194
		mu 0 3 250 252 2193
		f 3 -550 -2554 -6904
		mu 0 3 251 249 1078
		f 3 -4752 -2555 -546
		mu 0 3 248 1077 249
		f 3 -4763 -4753 -544
		mu 0 3 247 1759 248
		f 3 -542 -4775 -4764
		mu 0 3 247 245 1761
		f 3 6904 -541 -549
		mu 0 3 250 244 246
		f 3 -6905 -6195 -537
		mu 0 3 244 250 243
		f 3 -538 -530 -4777
		mu 0 3 245 242 240
		f 3 -4779 -524 -518
		mu 0 3 237 240 238
		f 3 -4782 -516 -2103
		mu 0 3 909 237 235
		f 3 -2104 -512 -2095
		mu 0 3 906 235 234
		f 3 -2098 -510 6905
		mu 0 3 194 234 233
		f 3 -521 -502 -515
		mu 0 3 236 231 232
		f 3 -523 6906 -500
		mu 0 3 231 239 228
		f 3 -529 -492 -6907
		mu 0 3 239 227 228
		f 3 -535 -488 -528
		mu 0 3 241 226 227
		f 3 -6200 -486 -534
		mu 0 3 243 225 226
		f 3 -6231 -484 -6844
		mu 0 3 2199 223 225
		f 3 -490 -482 -478
		mu 0 3 221 224 222
		f 3 -496 -476 6907
		mu 0 3 230 221 218
		f 3 6908 -6908 6909
		mu 0 3 204 230 218
		f 3 -480 -6229 -475
		mu 0 3 220 223 219
		f 3 -6233 -466 -473
		mu 0 3 219 215 217
		f 3 -6235 -462 -6232
		mu 0 3 2205 214 215
		f 3 -6241 -461 -6234
		mu 0 3 2204 213 214
		f 3 -6645 -458 -6243
		mu 0 3 2209 212 213
		f 3 -6633 -6656 -456
		mu 0 3 212 2350 211
		f 3 -455 -6655 -6802
		mu 0 3 208 211 2356
		f 3 -464 -452 6910
		mu 0 3 216 210 209
		f 3 -6911 -450 6911
		mu 0 3 216 209 206
		f 3 -6801 6912 -449
		mu 0 3 208 2357 207
		f 3 -6913 6913 6914
		mu 0 3 207 2357 180
		f 3 -447 6915 6916
		mu 0 3 203 207 183
		f 3 -469 -6912 -444
		mu 0 3 205 216 206
		f 3 -6910 -470 -442
		mu 0 3 204 218 205
		f 3 -499 -6909 -440
		mu 0 3 202 230 204
		f 3 -6917 6917 -439
		mu 0 3 203 183 200
		f 3 -436 -505 -498
		mu 0 3 202 201 229
		f 3 6918 6919 -429
		mu 0 3 199 186 197
		f 3 -509 -434 -426
		mu 0 3 196 201 198
		f 3 6920 6921 -424
		mu 0 3 197 188 195
		f 3 -6906 -508 -422
		mu 0 3 194 233 196
		f 3 -2093 -2097 -418
		mu 0 3 193 907 194
		f 3 -4785 -416 -2077
		mu 0 3 902 193 192
		f 3 -414 -4793 -2081
		mu 0 3 192 190 864
		f 3 -412 -420 -6922
		mu 0 3 188 191 195
		f 3 -4792 -410 -1946
		mu 0 3 860 190 189
		f 3 -408 -4798 -1944
		mu 0 3 189 187 859
		f 3 -6920 -406 -6921
		mu 0 3 197 186 188
		f 3 -402 -6919 -431
		mu 0 3 184 186 199
		f 3 -405 -400 6922
		mu 0 3 187 185 182
		f 3 -6918 -398 -433
		mu 0 3 200 183 184
		f 3 -6916 -6915 -396
		mu 0 3 183 207 180
		f 3 -6923 -394 -4802
		mu 0 3 187 182 181
		f 3 -390 -6914 -6661
		mu 0 3 179 180 2357
		f 3 6923 -388 -6800
		mu 0 3 2364 175 179
		f 3 -4807 -393 -386
		mu 0 3 177 181 178
		f 3 -4809 -384 -5649
		mu 0 3 1767 177 176
		f 3 -6682 -380 -6924
		mu 0 3 2364 174 175
		f 3 -4826 -382 -376
		mu 0 3 172 176 173
		f 3 -374 -4829 -4824
		mu 0 3 172 171 1771
		f 3 -370 -378 -6681
		mu 0 3 169 170 174
		f 3 -368 -6679 6924
		mu 0 3 166 169 162
		f 3 -366 -5648 -373
		mu 0 3 168 167 171
		f 3 -5376 -5382 -364
		mu 0 3 165 1993 167
		f 3 -5375 -360 -5366
		mu 0 3 1990 165 164
		f 3 -6925 -356 -362
		mu 0 3 166 162 163
		f 3 -6799 -355 -6675
		mu 0 3 2362 161 162
		f 3 -352 -6798 -6791
		mu 0 3 159 161 2395
		f 3 -5364 -358 -350
		mu 0 3 158 164 160
		f 3 -6790 -348 -6709
		mu 0 3 2376 157 159
		f 3 -5358 -5363 -346
		mu 0 3 156 1988 158
		f 3 -344 -6788 6925
		mu 0 3 155 157 2394
		f 3 6926 -5355 -342
		mu 0 3 153 1986 156
		f 3 -6784 -341 -6926
		mu 0 3 2394 154 155
		f 3 -5349 -6927 -336
		mu 0 3 151 1986 153
		f 3 -6787 -335 -338
		mu 0 3 154 149 152
		f 3 -332 -5386 -5347
		mu 0 3 151 150 1984
		f 3 6927 -5387 -330
		mu 0 3 148 1982 150
		f 3 -329 -6786 -6508
		mu 0 3 147 149 2302
		f 3 -5338 -6928 -326
		mu 0 3 146 1982 148;
	setAttr ".fc[4500:4711]"
		f 3 -6505 6928 -324
		mu 0 3 147 2265 144
		f 3 -322 -5337 -5339
		mu 0 3 146 145 1983
		f 3 -5336 -320 -5290
		mu 0 3 1966 145 143
		f 3 6929 -318 -6929
		mu 0 3 2265 141 144
		f 3 6930 -5289 -316
		mu 0 3 142 1965 143
		f 3 6931 6932 -6931
		mu 0 3 142 2401 1965
		f 3 6933 -6932 -314
		mu 0 3 140 2401 142
		f 3 -6930 -6378 -312
		mu 0 3 141 2265 138
		f 3 -307 -6380 -6386
		mu 0 3 135 138 2266
		f 3 6934 -304 -302
		mu 0 3 134 137 136
		f 3 6935 -301 -6388
		mu 0 3 2268 115 135
		f 3 -294 6936 6937
		mu 0 3 133 132 2402
		f 3 -6937 6938 6939
		mu 0 3 2402 132 2403
		f 3 6940 -6940 6941
		mu 0 3 2404 2402 2403
		f 3 6942 6943 -6941
		mu 0 3 2404 2405 2402
		f 3 6944 -6943 6945
		mu 0 3 2406 2405 2404
		f 3 6946 -6946 6947
		mu 0 3 2407 2406 2404
		f 3 -6939 6948 6949
		mu 0 3 2403 132 2408
		f 3 -6950 6950 6951
		mu 0 3 2403 2408 2409
		f 3 6952 -6951 6953
		mu 0 3 130 2409 2408
		f 3 6954 -6938 -6944
		mu 0 3 2405 133 2402
		f 3 -292 -6954 -6949
		mu 0 3 132 130 2408
		f 3 6955 -290 -297
		mu 0 3 115 118 131
		f 3 -6953 -288 6956
		mu 0 3 2409 130 128
		f 3 -6957 -282 6957
		mu 0 3 2409 128 127
		f 3 -6958 -280 6958
		mu 0 3 2409 127 126
		f 3 -276 -285 6959
		mu 0 3 122 125 129
		f 3 6960 6961 -274
		mu 0 3 123 2410 124
		f 3 6962 -6961 6963
		mu 0 3 2411 2410 123
		f 3 6964 6965 -6964
		mu 0 3 123 2412 2411
		f 3 -6965 6966 6967
		mu 0 3 2412 123 2413
		f 3 -6967 6968 6969
		mu 0 3 2413 123 2414
		f 3 6970 -6969 -272
		mu 0 3 121 2414 123
		f 3 6971 6972 -6971
		mu 0 3 121 2415 2414
		f 3 6973 -270 -6960
		mu 0 3 129 119 122
		f 3 -6972 -268 6974
		mu 0 3 2415 121 120
		f 3 -6975 6975 6976
		mu 0 3 2415 120 2416
		f 3 -6976 6977 6978
		mu 0 3 2416 120 2417
		f 3 6979 6980 -6979
		mu 0 3 2417 2418 2416
		f 3 6981 6982 -6980
		mu 0 3 2417 2419 2418
		f 3 6983 6984 -6983
		mu 0 3 2419 2420 2418
		f 3 6985 6986 -6984
		mu 0 3 2419 2421 2420
		f 3 6987 6988 -6986
		mu 0 3 2419 2422 2421
		f 3 6989 -6988 6990
		mu 0 3 19 2422 2419
		f 3 6991 -6991 6992
		mu 0 3 2423 19 2419
		f 3 6993 -6990 6994
		mu 0 3 2424 2422 19
		f 3 6995 6996 -6995
		mu 0 3 19 2425 2424
		f 3 -6997 6997 6998
		mu 0 3 2424 2425 2426
		f 3 6999 7000 -6998
		mu 0 3 2425 2427 2426
		f 3 7001 -7001 7002
		mu 0 3 2428 2426 2427
		f 3 7003 -7003 7004
		mu 0 3 2429 2428 2427
		f 3 -7005 7005 7006
		mu 0 3 2429 2427 2430
		f 3 7007 -7007 7008
		mu 0 3 2431 2429 2430
		f 3 -7009 7009 7010
		mu 0 3 2431 2430 16
		f 3 7011 7012 -7010
		mu 0 3 2430 2432 16
		f 3 7013 7014 -7008
		mu 0 3 2431 2433 2429
		f 3 -7006 7015 -7012
		mu 0 3 2430 2427 2432
		f 3 -7015 7016 -7004
		mu 0 3 2429 2433 2428
		f 3 -7000 7017 -7016
		mu 0 3 2427 2425 2432
		f 3 7018 -7018 7019
		mu 0 3 17 2432 2425
		f 3 7020 -6993 -6982
		mu 0 3 2417 2423 2419
		f 3 -7021 7021 7022
		mu 0 3 2423 2417 2434
		f 3 7023 7024 -7023
		mu 0 3 2434 2435 2423
		f 3 -7025 7025 7026
		mu 0 3 2423 2435 20
		f 3 7027 7028 -7024
		mu 0 3 2434 107 2435
		f 3 7029 7030 -7029
		mu 0 3 107 102 2435
		f 3 -7031 7031 7032
		mu 0 3 2435 102 26
		f 3 -7028 7033 7034
		mu 0 3 107 2434 2436
		f 3 -7022 7035 -7034
		mu 0 3 2434 2417 2436
		f 3 -6978 7036 -7036
		mu 0 3 2417 120 2436
		f 3 -266 7037 -7037
		mu 0 3 120 117 2436
		f 3 7038 7039 -7038
		mu 0 3 117 108 2436
		f 3 -264 -6974 -287
		mu 0 3 118 119 129
		f 3 -6956 -258 -262
		mu 0 3 118 115 116
		f 3 -257 -6936 7040
		mu 0 3 114 115 2268
		f 3 -254 -7041 -6392
		mu 0 3 113 114 2268
		f 3 -6502 -252 -6391
		mu 0 3 2269 112 113
		f 3 -250 -6416 7041
		mu 0 3 111 112 2275
		f 3 -7042 -6422 -248
		mu 0 3 111 2275 109
		f 3 -7039 -260 -246
		mu 0 3 108 117 110
		f 3 7042 -245 -6421
		mu 0 3 100 106 109
		f 3 -7035 -7040 -242
		mu 0 3 107 2436 108
		f 3 -240 -236 -7030
		mu 0 3 107 105 102
		f 3 -7043 -225 -238
		mu 0 3 106 100 101
		f 3 -232 -221 7043
		mu 0 3 104 99 98
		f 3 7044 7045 -7044
		mu 0 3 98 43 104
		f 3 7046 -7046 7047
		mu 0 3 2437 104 43
		f 3 -7047 7048 7049
		mu 0 3 104 2437 32
		f 3 -7049 7050 7051
		mu 0 3 32 2437 42
		f 3 -7045 7052 7053
		mu 0 3 43 98 47
		f 3 -223 -6419 -217
		mu 0 3 97 100 94
		f 3 -219 -215 7054
		mu 0 3 98 96 95
		f 3 7055 7056 -7055
		mu 0 3 95 89 98
		f 3 7057 -212 -6417
		mu 0 3 2274 93 94
		f 3 7058 -209 -7058
		mu 0 3 2274 92 93
		f 3 -207 -7059 -6498
		mu 0 3 91 92 2274
		f 3 -6497 7059 -205
		mu 0 3 91 2297 88
		f 3 -203 -7056 -213
		mu 0 3 90 89 95
		f 3 -7057 -201 -7053
		mu 0 3 98 89 47
		f 3 -6477 -199 -7060
		mu 0 3 2297 87 88
		f 3 -6474 -6486 -197
		mu 0 3 87 2296 86
		f 3 -190 -196 -6488
		mu 0 3 84 85 86
		f 3 -6492 7060 -187
		mu 0 3 84 2300 83
		f 3 -7061 7061 7062
		mu 0 3 83 2300 2438
		f 3 7063 7064 -7062
		mu 0 3 2300 2439 2438
		f 3 7065 -7065 7066
		mu 0 3 2440 2438 2439
		f 3 -7067 7067 7068
		mu 0 3 2440 2439 2441
		f 3 -7069 7069 7070
		mu 0 3 2440 2441 78
		f 3 7071 7072 -7070
		mu 0 3 2441 2442 78
		f 3 7073 -7073 7074
		mu 0 3 2443 78 2442
		f 3 7075 7076 -7074
		mu 0 3 2443 2444 78
		f 3 -7077 7077 7078
		mu 0 3 78 2444 74
		f 3 7079 -7078 7080
		mu 0 3 2445 74 2444
		f 3 7081 -7066 7082
		mu 0 3 79 2438 2440
		f 3 -185 -7063 7083
		mu 0 3 80 83 2438
		f 3 -7084 -7082 -176
		mu 0 3 80 2438 79
		f 3 -7083 -7071 -172
		mu 0 3 79 2440 78
		f 3 -161 -171 -7079
		mu 0 3 74 75 78
		f 3 7084 -158 -7080
		mu 0 3 2445 72 74
		f 3 7085 7086 -7085
		mu 0 3 2445 2446 72
		f 3 7087 7088 -7086
		mu 0 3 2445 2447 2446
		f 3 7089 7090 -7089
		mu 0 3 2447 2448 2446
		f 3 -7091 7091 7092
		mu 0 3 2446 2448 2449
		f 3 7093 -7092 7094
		mu 0 3 2450 2449 2448
		f 3 7095 7096 -7095
		mu 0 3 2448 2451 2450
		f 3 7097 7098 -7097
		mu 0 3 2451 2452 2450
		f 3 7099 7100 -7099
		mu 0 3 2452 2453 2450
		f 3 -7094 -7101 7101
		mu 0 3 2449 2450 2453
		f 3 -7102 7102 7103
		mu 0 3 2449 2453 70
		f 3 7104 -7093 7105
		mu 0 3 71 2446 2449
		f 3 7106 -7096 -7090
		mu 0 3 2447 2451 2448
		f 3 -7107 7107 7108
		mu 0 3 2451 2447 2454
		f 3 7109 -7109 7110
		mu 0 3 2455 2451 2454
		f 3 -7105 -154 -7087
		mu 0 3 2446 71 72
		f 3 -7106 -7104 -152
		mu 0 3 71 2449 70
		f 3 -157 -148 -164
		mu 0 3 73 69 67
		f 3 -165 -144 7111
		mu 0 3 76 67 65
		f 3 -143 7112 7113
		mu 0 3 64 66 57
		f 3 -167 -7112 -140
		mu 0 3 63 76 65
		f 3 -139 -7114 7114
		mu 0 3 62 64 57
		f 3 7115 -168 -136
		mu 0 3 61 77 63
		f 3 -135 -7115 7116
		mu 0 3 60 62 57
		f 3 -175 -7116 -132
		mu 0 3 59 77 61
		f 3 -131 -7117 -126
		mu 0 3 58 60 57
		f 3 -124 7117 7118
		mu 0 3 56 57 2456
		f 3 7119 7120 -7118
		mu 0 3 57 2457 2456
		f 3 7121 -7121 7122
		mu 0 3 2458 2456 2457
		f 3 -7122 7123 7124
		mu 0 3 2456 2458 37
		f 3 7125 7126 -7124
		mu 0 3 2458 2459 37
		f 3 7127 7128 -7127
		mu 0 3 2459 2460 37
		f 3 -7129 7129 7130
		mu 0 3 37 2460 33
		f 3 7131 7132 -7130
		mu 0 3 2460 2461 33
		f 3 7133 -7133 7134
		mu 0 3 4 33 2461
		f 3 7135 -7132 7136
		mu 0 3 2462 2461 2460
		f 3 -7137 -7128 7137
		mu 0 3 2462 2460 2459
		f 3 -7138 7138 7139
		mu 0 3 2462 2459 2463
		f 3 7140 -7140 7141
		mu 0 3 2464 2462 2463
		f 3 7142 -7142 7143
		mu 0 3 2458 2464 2463
		f 3 -7144 -7139 -7126
		mu 0 3 2458 2463 2459
		f 3 7144 -7125 7145
		mu 0 3 52 2456 37
		f 3 -7119 -7145 -122
		mu 0 3 56 2456 52
		f 3 -181 -128 -120
		mu 0 3 54 59 55
		f 3 7146 -182 -118
		mu 0 3 53 82 54
		f 3 -116 -191 -7147
		mu 0 3 53 51 82
		f 3 -108 -113 7147
		mu 0 3 49 50 38
		f 3 -111 -102 -193
		mu 0 3 51 48 47
		f 3 -99 -105 7148
		mu 0 3 45 46 40
		f 3 -7054 -100 -94
		mu 0 3 43 47 44
		f 3 -7051 -7048 -92
		mu 0 3 42 2437 43
		f 3 -97 -7149 -86
		mu 0 3 41 45 40
		f 3 -7148 -84 -107
		mu 0 3 49 38 40
		f 3 -115 -7146 -81
		mu 0 3 38 52 37
		f 3 -83 -76 -88
		mu 0 3 39 36 35
		f 3 -7052 -91 -74
		mu 0 3 32 42 35
		f 3 -7131 -73 -78
		mu 0 3 37 33 34
		f 3 -71 -7134 7149
		mu 0 3 31 33 4
		f 3 7150 -7050 -68
		mu 0 3 30 104 32
		f 3 -7151 -62 -234
		mu 0 3 104 30 27
		f 3 7151 -60 7152
		mu 0 3 2465 28 29
		f 3 -7153 7153 7154
		mu 0 3 2465 29 1
		f 3 -7152 7155 7156
		mu 0 3 28 2465 21
		f 3 7157 -7157 7158
		mu 0 3 24 28 21
		f 3 7159 -7156 7160
		mu 0 3 0 21 2465
		f 3 -7160 7161 7162
		mu 0 3 21 0 15
		f 3 -7032 -235 -56
		mu 0 3 26 102 27
		f 3 -7033 -54 7163
		mu 0 3 2435 26 23
		f 3 -58 -7158 -52
		mu 0 3 25 28 24
		f 3 -7026 -7164 -48
		mu 0 3 20 2435 23
		f 3 -51 -7159 -47
		mu 0 3 22 24 21
		f 3 -7027 -42 -6992
		mu 0 3 2423 20 19
		f 3 -40 -7020 -6996
		mu 0 3 19 17 2425
		f 3 -38 -45 -7163
		mu 0 3 15 18 21
		f 3 -36 -7013 -7019
		mu 0 3 17 16 2432
		f 3 7164 -34 7165
		mu 0 3 2466 16 14
		f 3 -7166 -30 7166
		mu 0 3 2466 14 13
		f 3 -7167 7167 7168
		mu 0 3 2466 13 2467
		f 3 -28 7169 -7168
		mu 0 3 13 12 2467
		f 3 -7170 7170 7171
		mu 0 3 2467 12 2468
		f 3 -7171 7172 7173
		mu 0 3 2468 12 7
		f 3 7174 -7174 7175
		mu 0 3 2469 2468 7
		f 3 7176 -7175 7177
		mu 0 3 2470 2468 2469
		f 3 7178 -7172 -7177
		mu 0 3 2470 2467 2468
		f 3 7179 -7179 7180
		mu 0 3 2471 2467 2470
		f 3 -7162 -23 -33
		mu 0 3 15 0 11
		f 3 -16 -27 -20
		mu 0 3 9 8 10
		f 3 -7173 -26 -14
		mu 0 3 7 12 8
		f 3 -7176 -12 7181
		mu 0 3 2469 7 6
		f 3 -10 7182 -7182
		mu 0 3 6 4 2469
		f 3 -67 -7150 -6
		mu 0 3 3 31 4
		f 3 -4 -7154 -66
		mu 0 3 3 1 29
		f 3 -3 -9 -18
		mu 0 3 0 2 5
		f 3 -7161 -7155 -1
		mu 0 3 0 2465 1;
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
createNode skinCluster -n "Helmet_skinCluster";
	rename -uid "951B8724-4E8C-B807-B071-91B396CE050B";
	setAttr -s 2472 ".wl";
	setAttr ".wl[0:499].w"
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1;
	setAttr ".wl[500:999].w"
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1;
	setAttr ".wl[1000:1499].w"
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1;
	setAttr ".wl[1500:1999].w"
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1;
	setAttr ".wl[2000:2471].w"
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1
		1 8 1;
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
	rename -uid "A965E3E2-434D-AA92-CD8A-F18474D00F94";
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
connectAttr "Helmet_skinCluster.og[0]" "HelmetShape.i";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "HelmetShapeOrig.w" "Helmet_skinCluster.ip[0].ig";
connectAttr "HelmetShapeOrig.o" "Helmet_skinCluster.orggeom[0]";
connectAttr "pelvis.wm" "Helmet_skinCluster.ma[0]";
connectAttr "spine_01.wm" "Helmet_skinCluster.ma[1]";
connectAttr "spine_02.wm" "Helmet_skinCluster.ma[2]";
connectAttr "spine_03.wm" "Helmet_skinCluster.ma[3]";
connectAttr "spine_04.wm" "Helmet_skinCluster.ma[4]";
connectAttr "spine_05.wm" "Helmet_skinCluster.ma[5]";
connectAttr "neck_01.wm" "Helmet_skinCluster.ma[6]";
connectAttr "neck_02.wm" "Helmet_skinCluster.ma[7]";
connectAttr "head.wm" "Helmet_skinCluster.ma[8]";
connectAttr "clavicle_l.wm" "Helmet_skinCluster.ma[9]";
connectAttr "upperarm_l.wm" "Helmet_skinCluster.ma[10]";
connectAttr "lowerarm_l.wm" "Helmet_skinCluster.ma[11]";
connectAttr "lowerarm_twist_02_l.wm" "Helmet_skinCluster.ma[12]";
connectAttr "lowerarm_twist_01_l.wm" "Helmet_skinCluster.ma[13]";
connectAttr "hand_l.wm" "Helmet_skinCluster.ma[14]";
connectAttr "middle_metacarpal_l.wm" "Helmet_skinCluster.ma[15]";
connectAttr "middle_01_l.wm" "Helmet_skinCluster.ma[16]";
connectAttr "middle_02_l.wm" "Helmet_skinCluster.ma[17]";
connectAttr "middle_03_l.wm" "Helmet_skinCluster.ma[18]";
connectAttr "pinky_metacarpal_l.wm" "Helmet_skinCluster.ma[19]";
connectAttr "pinky_01_l.wm" "Helmet_skinCluster.ma[20]";
connectAttr "pinky_02_l.wm" "Helmet_skinCluster.ma[21]";
connectAttr "pinky_03_l.wm" "Helmet_skinCluster.ma[22]";
connectAttr "ring_metacarpal_l.wm" "Helmet_skinCluster.ma[23]";
connectAttr "ring_01_l.wm" "Helmet_skinCluster.ma[24]";
connectAttr "ring_02_l.wm" "Helmet_skinCluster.ma[25]";
connectAttr "ring_03_l.wm" "Helmet_skinCluster.ma[26]";
connectAttr "thumb_01_l.wm" "Helmet_skinCluster.ma[27]";
connectAttr "thumb_02_l.wm" "Helmet_skinCluster.ma[28]";
connectAttr "thumb_03_l.wm" "Helmet_skinCluster.ma[29]";
connectAttr "index_metacarpal_l.wm" "Helmet_skinCluster.ma[30]";
connectAttr "index_01_l.wm" "Helmet_skinCluster.ma[31]";
connectAttr "index_02_l.wm" "Helmet_skinCluster.ma[32]";
connectAttr "index_03_l.wm" "Helmet_skinCluster.ma[33]";
connectAttr "upperarm_twist_01_l.wm" "Helmet_skinCluster.ma[34]";
connectAttr "upperarm_twist_02_l.wm" "Helmet_skinCluster.ma[35]";
connectAttr "clavicle_r.wm" "Helmet_skinCluster.ma[36]";
connectAttr "upperarm_r.wm" "Helmet_skinCluster.ma[37]";
connectAttr "lowerarm_r.wm" "Helmet_skinCluster.ma[38]";
connectAttr "lowerarm_twist_02_r.wm" "Helmet_skinCluster.ma[39]";
connectAttr "lowerarm_twist_01_r.wm" "Helmet_skinCluster.ma[40]";
connectAttr "hand_r.wm" "Helmet_skinCluster.ma[41]";
connectAttr "middle_metacarpal_r.wm" "Helmet_skinCluster.ma[42]";
connectAttr "middle_01_r.wm" "Helmet_skinCluster.ma[43]";
connectAttr "middle_02_r.wm" "Helmet_skinCluster.ma[44]";
connectAttr "middle_03_r.wm" "Helmet_skinCluster.ma[45]";
connectAttr "pinky_metacarpal_r.wm" "Helmet_skinCluster.ma[46]";
connectAttr "pinky_01_r.wm" "Helmet_skinCluster.ma[47]";
connectAttr "pinky_02_r.wm" "Helmet_skinCluster.ma[48]";
connectAttr "pinky_03_r.wm" "Helmet_skinCluster.ma[49]";
connectAttr "ring_metacarpal_r.wm" "Helmet_skinCluster.ma[50]";
connectAttr "ring_01_r.wm" "Helmet_skinCluster.ma[51]";
connectAttr "ring_02_r.wm" "Helmet_skinCluster.ma[52]";
connectAttr "ring_03_r.wm" "Helmet_skinCluster.ma[53]";
connectAttr "thumb_01_r.wm" "Helmet_skinCluster.ma[54]";
connectAttr "thumb_02_r.wm" "Helmet_skinCluster.ma[55]";
connectAttr "thumb_03_r.wm" "Helmet_skinCluster.ma[56]";
connectAttr "index_metacarpal_r.wm" "Helmet_skinCluster.ma[57]";
connectAttr "index_01_r.wm" "Helmet_skinCluster.ma[58]";
connectAttr "index_02_r.wm" "Helmet_skinCluster.ma[59]";
connectAttr "index_03_r.wm" "Helmet_skinCluster.ma[60]";
connectAttr "upperarm_twist_01_r.wm" "Helmet_skinCluster.ma[61]";
connectAttr "upperarm_twist_02_r.wm" "Helmet_skinCluster.ma[62]";
connectAttr "thigh_r.wm" "Helmet_skinCluster.ma[63]";
connectAttr "calf_r.wm" "Helmet_skinCluster.ma[64]";
connectAttr "foot_r.wm" "Helmet_skinCluster.ma[65]";
connectAttr "ball_r.wm" "Helmet_skinCluster.ma[66]";
connectAttr "calf_twist_02_r.wm" "Helmet_skinCluster.ma[67]";
connectAttr "calf_twist_01_r.wm" "Helmet_skinCluster.ma[68]";
connectAttr "thigh_twist_01_r.wm" "Helmet_skinCluster.ma[69]";
connectAttr "thigh_twist_02_r.wm" "Helmet_skinCluster.ma[70]";
connectAttr "thigh_l.wm" "Helmet_skinCluster.ma[71]";
connectAttr "calf_l.wm" "Helmet_skinCluster.ma[72]";
connectAttr "foot_l.wm" "Helmet_skinCluster.ma[73]";
connectAttr "ball_l.wm" "Helmet_skinCluster.ma[74]";
connectAttr "calf_twist_02_l.wm" "Helmet_skinCluster.ma[75]";
connectAttr "calf_twist_01_l.wm" "Helmet_skinCluster.ma[76]";
connectAttr "thigh_twist_01_l.wm" "Helmet_skinCluster.ma[77]";
connectAttr "thigh_twist_02_l.wm" "Helmet_skinCluster.ma[78]";
connectAttr "pelvis.liw" "Helmet_skinCluster.lw[0]";
connectAttr "spine_01.liw" "Helmet_skinCluster.lw[1]";
connectAttr "spine_02.liw" "Helmet_skinCluster.lw[2]";
connectAttr "spine_03.liw" "Helmet_skinCluster.lw[3]";
connectAttr "spine_04.liw" "Helmet_skinCluster.lw[4]";
connectAttr "spine_05.liw" "Helmet_skinCluster.lw[5]";
connectAttr "neck_01.liw" "Helmet_skinCluster.lw[6]";
connectAttr "neck_02.liw" "Helmet_skinCluster.lw[7]";
connectAttr "head.liw" "Helmet_skinCluster.lw[8]";
connectAttr "clavicle_l.liw" "Helmet_skinCluster.lw[9]";
connectAttr "upperarm_l.liw" "Helmet_skinCluster.lw[10]";
connectAttr "lowerarm_l.liw" "Helmet_skinCluster.lw[11]";
connectAttr "lowerarm_twist_02_l.liw" "Helmet_skinCluster.lw[12]";
connectAttr "lowerarm_twist_01_l.liw" "Helmet_skinCluster.lw[13]";
connectAttr "hand_l.liw" "Helmet_skinCluster.lw[14]";
connectAttr "middle_metacarpal_l.liw" "Helmet_skinCluster.lw[15]";
connectAttr "middle_01_l.liw" "Helmet_skinCluster.lw[16]";
connectAttr "middle_02_l.liw" "Helmet_skinCluster.lw[17]";
connectAttr "middle_03_l.liw" "Helmet_skinCluster.lw[18]";
connectAttr "pinky_metacarpal_l.liw" "Helmet_skinCluster.lw[19]";
connectAttr "pinky_01_l.liw" "Helmet_skinCluster.lw[20]";
connectAttr "pinky_02_l.liw" "Helmet_skinCluster.lw[21]";
connectAttr "pinky_03_l.liw" "Helmet_skinCluster.lw[22]";
connectAttr "ring_metacarpal_l.liw" "Helmet_skinCluster.lw[23]";
connectAttr "ring_01_l.liw" "Helmet_skinCluster.lw[24]";
connectAttr "ring_02_l.liw" "Helmet_skinCluster.lw[25]";
connectAttr "ring_03_l.liw" "Helmet_skinCluster.lw[26]";
connectAttr "thumb_01_l.liw" "Helmet_skinCluster.lw[27]";
connectAttr "thumb_02_l.liw" "Helmet_skinCluster.lw[28]";
connectAttr "thumb_03_l.liw" "Helmet_skinCluster.lw[29]";
connectAttr "index_metacarpal_l.liw" "Helmet_skinCluster.lw[30]";
connectAttr "index_01_l.liw" "Helmet_skinCluster.lw[31]";
connectAttr "index_02_l.liw" "Helmet_skinCluster.lw[32]";
connectAttr "index_03_l.liw" "Helmet_skinCluster.lw[33]";
connectAttr "upperarm_twist_01_l.liw" "Helmet_skinCluster.lw[34]";
connectAttr "upperarm_twist_02_l.liw" "Helmet_skinCluster.lw[35]";
connectAttr "clavicle_r.liw" "Helmet_skinCluster.lw[36]";
connectAttr "upperarm_r.liw" "Helmet_skinCluster.lw[37]";
connectAttr "lowerarm_r.liw" "Helmet_skinCluster.lw[38]";
connectAttr "lowerarm_twist_02_r.liw" "Helmet_skinCluster.lw[39]";
connectAttr "lowerarm_twist_01_r.liw" "Helmet_skinCluster.lw[40]";
connectAttr "hand_r.liw" "Helmet_skinCluster.lw[41]";
connectAttr "middle_metacarpal_r.liw" "Helmet_skinCluster.lw[42]";
connectAttr "middle_01_r.liw" "Helmet_skinCluster.lw[43]";
connectAttr "middle_02_r.liw" "Helmet_skinCluster.lw[44]";
connectAttr "middle_03_r.liw" "Helmet_skinCluster.lw[45]";
connectAttr "pinky_metacarpal_r.liw" "Helmet_skinCluster.lw[46]";
connectAttr "pinky_01_r.liw" "Helmet_skinCluster.lw[47]";
connectAttr "pinky_02_r.liw" "Helmet_skinCluster.lw[48]";
connectAttr "pinky_03_r.liw" "Helmet_skinCluster.lw[49]";
connectAttr "ring_metacarpal_r.liw" "Helmet_skinCluster.lw[50]";
connectAttr "ring_01_r.liw" "Helmet_skinCluster.lw[51]";
connectAttr "ring_02_r.liw" "Helmet_skinCluster.lw[52]";
connectAttr "ring_03_r.liw" "Helmet_skinCluster.lw[53]";
connectAttr "thumb_01_r.liw" "Helmet_skinCluster.lw[54]";
connectAttr "thumb_02_r.liw" "Helmet_skinCluster.lw[55]";
connectAttr "thumb_03_r.liw" "Helmet_skinCluster.lw[56]";
connectAttr "index_metacarpal_r.liw" "Helmet_skinCluster.lw[57]";
connectAttr "index_01_r.liw" "Helmet_skinCluster.lw[58]";
connectAttr "index_02_r.liw" "Helmet_skinCluster.lw[59]";
connectAttr "index_03_r.liw" "Helmet_skinCluster.lw[60]";
connectAttr "upperarm_twist_01_r.liw" "Helmet_skinCluster.lw[61]";
connectAttr "upperarm_twist_02_r.liw" "Helmet_skinCluster.lw[62]";
connectAttr "thigh_r.liw" "Helmet_skinCluster.lw[63]";
connectAttr "calf_r.liw" "Helmet_skinCluster.lw[64]";
connectAttr "foot_r.liw" "Helmet_skinCluster.lw[65]";
connectAttr "ball_r.liw" "Helmet_skinCluster.lw[66]";
connectAttr "calf_twist_02_r.liw" "Helmet_skinCluster.lw[67]";
connectAttr "calf_twist_01_r.liw" "Helmet_skinCluster.lw[68]";
connectAttr "thigh_twist_01_r.liw" "Helmet_skinCluster.lw[69]";
connectAttr "thigh_twist_02_r.liw" "Helmet_skinCluster.lw[70]";
connectAttr "thigh_l.liw" "Helmet_skinCluster.lw[71]";
connectAttr "calf_l.liw" "Helmet_skinCluster.lw[72]";
connectAttr "foot_l.liw" "Helmet_skinCluster.lw[73]";
connectAttr "ball_l.liw" "Helmet_skinCluster.lw[74]";
connectAttr "calf_twist_02_l.liw" "Helmet_skinCluster.lw[75]";
connectAttr "calf_twist_01_l.liw" "Helmet_skinCluster.lw[76]";
connectAttr "thigh_twist_01_l.liw" "Helmet_skinCluster.lw[77]";
connectAttr "thigh_twist_02_l.liw" "Helmet_skinCluster.lw[78]";
connectAttr "pelvis.obcc" "Helmet_skinCluster.ifcl[0]";
connectAttr "spine_01.obcc" "Helmet_skinCluster.ifcl[1]";
connectAttr "spine_02.obcc" "Helmet_skinCluster.ifcl[2]";
connectAttr "spine_03.obcc" "Helmet_skinCluster.ifcl[3]";
connectAttr "spine_04.obcc" "Helmet_skinCluster.ifcl[4]";
connectAttr "spine_05.obcc" "Helmet_skinCluster.ifcl[5]";
connectAttr "neck_01.obcc" "Helmet_skinCluster.ifcl[6]";
connectAttr "neck_02.obcc" "Helmet_skinCluster.ifcl[7]";
connectAttr "head.obcc" "Helmet_skinCluster.ifcl[8]";
connectAttr "clavicle_l.obcc" "Helmet_skinCluster.ifcl[9]";
connectAttr "upperarm_l.obcc" "Helmet_skinCluster.ifcl[10]";
connectAttr "lowerarm_l.obcc" "Helmet_skinCluster.ifcl[11]";
connectAttr "lowerarm_twist_02_l.obcc" "Helmet_skinCluster.ifcl[12]";
connectAttr "lowerarm_twist_01_l.obcc" "Helmet_skinCluster.ifcl[13]";
connectAttr "hand_l.obcc" "Helmet_skinCluster.ifcl[14]";
connectAttr "middle_metacarpal_l.obcc" "Helmet_skinCluster.ifcl[15]";
connectAttr "middle_01_l.obcc" "Helmet_skinCluster.ifcl[16]";
connectAttr "middle_02_l.obcc" "Helmet_skinCluster.ifcl[17]";
connectAttr "middle_03_l.obcc" "Helmet_skinCluster.ifcl[18]";
connectAttr "pinky_metacarpal_l.obcc" "Helmet_skinCluster.ifcl[19]";
connectAttr "pinky_01_l.obcc" "Helmet_skinCluster.ifcl[20]";
connectAttr "pinky_02_l.obcc" "Helmet_skinCluster.ifcl[21]";
connectAttr "pinky_03_l.obcc" "Helmet_skinCluster.ifcl[22]";
connectAttr "ring_metacarpal_l.obcc" "Helmet_skinCluster.ifcl[23]";
connectAttr "ring_01_l.obcc" "Helmet_skinCluster.ifcl[24]";
connectAttr "ring_02_l.obcc" "Helmet_skinCluster.ifcl[25]";
connectAttr "ring_03_l.obcc" "Helmet_skinCluster.ifcl[26]";
connectAttr "thumb_01_l.obcc" "Helmet_skinCluster.ifcl[27]";
connectAttr "thumb_02_l.obcc" "Helmet_skinCluster.ifcl[28]";
connectAttr "thumb_03_l.obcc" "Helmet_skinCluster.ifcl[29]";
connectAttr "index_metacarpal_l.obcc" "Helmet_skinCluster.ifcl[30]";
connectAttr "index_01_l.obcc" "Helmet_skinCluster.ifcl[31]";
connectAttr "index_02_l.obcc" "Helmet_skinCluster.ifcl[32]";
connectAttr "index_03_l.obcc" "Helmet_skinCluster.ifcl[33]";
connectAttr "upperarm_twist_01_l.obcc" "Helmet_skinCluster.ifcl[34]";
connectAttr "upperarm_twist_02_l.obcc" "Helmet_skinCluster.ifcl[35]";
connectAttr "clavicle_r.obcc" "Helmet_skinCluster.ifcl[36]";
connectAttr "upperarm_r.obcc" "Helmet_skinCluster.ifcl[37]";
connectAttr "lowerarm_r.obcc" "Helmet_skinCluster.ifcl[38]";
connectAttr "lowerarm_twist_02_r.obcc" "Helmet_skinCluster.ifcl[39]";
connectAttr "lowerarm_twist_01_r.obcc" "Helmet_skinCluster.ifcl[40]";
connectAttr "hand_r.obcc" "Helmet_skinCluster.ifcl[41]";
connectAttr "middle_metacarpal_r.obcc" "Helmet_skinCluster.ifcl[42]";
connectAttr "middle_01_r.obcc" "Helmet_skinCluster.ifcl[43]";
connectAttr "middle_02_r.obcc" "Helmet_skinCluster.ifcl[44]";
connectAttr "middle_03_r.obcc" "Helmet_skinCluster.ifcl[45]";
connectAttr "pinky_metacarpal_r.obcc" "Helmet_skinCluster.ifcl[46]";
connectAttr "pinky_01_r.obcc" "Helmet_skinCluster.ifcl[47]";
connectAttr "pinky_02_r.obcc" "Helmet_skinCluster.ifcl[48]";
connectAttr "pinky_03_r.obcc" "Helmet_skinCluster.ifcl[49]";
connectAttr "ring_metacarpal_r.obcc" "Helmet_skinCluster.ifcl[50]";
connectAttr "ring_01_r.obcc" "Helmet_skinCluster.ifcl[51]";
connectAttr "ring_02_r.obcc" "Helmet_skinCluster.ifcl[52]";
connectAttr "ring_03_r.obcc" "Helmet_skinCluster.ifcl[53]";
connectAttr "thumb_01_r.obcc" "Helmet_skinCluster.ifcl[54]";
connectAttr "thumb_02_r.obcc" "Helmet_skinCluster.ifcl[55]";
connectAttr "thumb_03_r.obcc" "Helmet_skinCluster.ifcl[56]";
connectAttr "index_metacarpal_r.obcc" "Helmet_skinCluster.ifcl[57]";
connectAttr "index_01_r.obcc" "Helmet_skinCluster.ifcl[58]";
connectAttr "index_02_r.obcc" "Helmet_skinCluster.ifcl[59]";
connectAttr "index_03_r.obcc" "Helmet_skinCluster.ifcl[60]";
connectAttr "upperarm_twist_01_r.obcc" "Helmet_skinCluster.ifcl[61]";
connectAttr "upperarm_twist_02_r.obcc" "Helmet_skinCluster.ifcl[62]";
connectAttr "thigh_r.obcc" "Helmet_skinCluster.ifcl[63]";
connectAttr "calf_r.obcc" "Helmet_skinCluster.ifcl[64]";
connectAttr "foot_r.obcc" "Helmet_skinCluster.ifcl[65]";
connectAttr "ball_r.obcc" "Helmet_skinCluster.ifcl[66]";
connectAttr "calf_twist_02_r.obcc" "Helmet_skinCluster.ifcl[67]";
connectAttr "calf_twist_01_r.obcc" "Helmet_skinCluster.ifcl[68]";
connectAttr "thigh_twist_01_r.obcc" "Helmet_skinCluster.ifcl[69]";
connectAttr "thigh_twist_02_r.obcc" "Helmet_skinCluster.ifcl[70]";
connectAttr "thigh_l.obcc" "Helmet_skinCluster.ifcl[71]";
connectAttr "calf_l.obcc" "Helmet_skinCluster.ifcl[72]";
connectAttr "foot_l.obcc" "Helmet_skinCluster.ifcl[73]";
connectAttr "ball_l.obcc" "Helmet_skinCluster.ifcl[74]";
connectAttr "calf_twist_02_l.obcc" "Helmet_skinCluster.ifcl[75]";
connectAttr "calf_twist_01_l.obcc" "Helmet_skinCluster.ifcl[76]";
connectAttr "thigh_twist_01_l.obcc" "Helmet_skinCluster.ifcl[77]";
connectAttr "thigh_twist_02_l.obcc" "Helmet_skinCluster.ifcl[78]";
connectAttr "bindPose1.msg" "Helmet_skinCluster.bp";
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
connectAttr "HelmetShape.iog" ":initialShadingGroup.dsm" -na;
// End of MainHero_Helmet.ma
