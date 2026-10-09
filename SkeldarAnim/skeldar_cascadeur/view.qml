import QtQuick

// The bridge window: a top-level Window, so it shows on its own. Plain QtQuick
// (no Qt Quick Controls, no QtWidgets): the model lives in window.py as the
// context property `bridge`.
Window {
    id: root
    visible: true
    width: 460
    height: 640
    title: "SkeldarAnim - Bridge"
    color: "#2b2d31"

    property var picked: []

    Column {
        x: 12
        y: 12
        width: root.width - 24
        spacing: 8

        Text {
            text: "SkeldarAnim - Bridge"
            color: "#e8e8e8"
            font.pixelSize: 16
            font.bold: true
        }
        Text {
            text: "Unreal animations - click to select, click again to clear"
            color: "#a8a8a8"
            font.pixelSize: 12
        }

        Row {
            spacing: 8
            Rectangle {
                width: root.width - 24 - 8 - 90
                height: 26
                radius: 4
                color: "#1e1f22"
                TextInput {
                    id: search
                    anchors.fill: parent
                    anchors.margins: 6
                    color: "#e8e8e8"
                    font.pixelSize: 13
                    onTextChanged: bridge.setFilter(text)
                }
            }
            Rectangle {
                width: 90
                height: 26
                radius: 4
                color: "#3c3f45"
                Text {
                    anchors.centerIn: parent
                    text: "Refresh"
                    color: "#e8e8e8"
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: bridge.refresh()
                }
            }
        }

        ListView {
            id: list
            width: root.width - 24
            height: 300
            clip: true
            model: bridge.clipNames
            delegate: Rectangle {
                width: list.width
                height: 22
                color: root.picked.indexOf(modelData) >= 0 ? "#4a4d55" : "transparent"
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    text: modelData
                    color: "#e8e8e8"
                    font.pixelSize: 13
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        var next = root.picked.slice()
                        var at = next.indexOf(modelData)
                        if (at >= 0) {
                            next.splice(at, 1)
                        } else {
                            next.push(modelData)
                        }
                        root.picked = next
                        bridge.pick(next)
                    }
                }
            }
        }

        Text {
            text: "Character - the clip is put on the chosen one"
            color: "#a8a8a8"
            font.pixelSize: 12
        }
        Row {
            spacing: 8
            Repeater {
                model: bridge.characterNames
                Rectangle {
                    width: 96
                    height: 128
                    radius: 6
                    color: modelData === bridge.characterName ? "#3c6e9c" : "#3c3f45"
                    Image {
                        x: 4
                        y: 4
                        width: 88
                        height: 88
                        source: bridge.characterPortraits[index]
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 6
                        text: modelData
                        color: "#ffffff"
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: bridge.pickCharacter(modelData)
                    }
                }
            }
        }

        Rectangle {
            width: root.width - 24
            height: 30
            radius: 4
            color: "#3c6e9c"
            Text {
                anchors.centerIn: parent
                text: "Import into Cascadeur"
                color: "#ffffff"
                font.pixelSize: 13
            }
            MouseArea {
                anchors.fill: parent
                onClicked: bridge.importPicked()
            }
        }

        Text {
            text: "Cascadeur scene"
            color: "#a8a8a8"
            font.pixelSize: 12
        }
        Text {
            text: bridge.targetText
            color: "#c8c8c8"
            font.pixelSize: 12
            width: root.width - 24
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: root.width - 24
            height: 30
            radius: 4
            color: "#8c5a2b"
            Text {
                anchors.centerIn: parent
                text: "Export to uasset"
                color: "#ffffff"
                font.pixelSize: 13
            }
            MouseArea {
                anchors.fill: parent
                onClicked: bridge.exportPicked()
            }
        }

        Row {
            spacing: 8
            Rectangle {
                width: (root.width - 24 - 8) / 2
                height: 26
                radius: 4
                color: "#1e1f22"
                TextInput {
                    id: author
                    anchors.fill: parent
                    anchors.margins: 6
                    color: "#e8e8e8"
                    font.pixelSize: 13
                    onTextChanged: bridge.setAuthor(text)
                }
                Text {
                    visible: author.text.length === 0
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: "author"
                    color: "#77787c"
                    font.pixelSize: 13
                }
            }
            Rectangle {
                width: (root.width - 24 - 8) / 2
                height: 26
                radius: 4
                color: "#1e1f22"
                TextInput {
                    id: upload
                    anchors.fill: parent
                    anchors.margins: 6
                    color: "#e8e8e8"
                    font.pixelSize: 13
                }
                Text {
                    visible: upload.text.length === 0
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: "name of the upload"
                    color: "#77787c"
                    font.pixelSize: 13
                }
            }
        }
        Rectangle {
            width: root.width - 24
            height: 30
            radius: 4
            color: "#3a7a4a"
            Text {
                anchors.centerIn: parent
                text: "Send to Shared"
                color: "#ffffff"
                font.pixelSize: 13
            }
            MouseArea {
                anchors.fill: parent
                onClicked: bridge.sendPicked(upload.text, author.text)
            }
        }

        Text {
            text: bridge.statusText
            color: "#e8e8e8"
            font.pixelSize: 12
            width: root.width - 24
            wrapMode: Text.WordWrap
        }
    }
}
