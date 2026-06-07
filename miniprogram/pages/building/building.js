// pages/building/building.js
const api = require('../../utils/api.js')

// 状态码映射: API返回数字 1=未售, 2=已签约, 3=锁定
const STATUS_MAP = {
  1: 'unsale',   // 未售(可售)
  2: 'signed',   // 已签约(已售)
  3: 'locked'    // 锁定(预留)
}

Page({
  data: {
    floors: [],       // 按楼层分组的数据 [{group, groupData}]
    loading: true,
    stats: { signed: 0, locked: 0, unsold: 0 }
  },

  onLoad(options) {
    this.buildingId = options.id
    this.loadUnits()
  },

  loadUnits() {
    this.setData({ loading: true })
    
    api.request('/api/buildings/' + this.buildingId + '/units').then(res => {
      const groups = res.data || []
      let signed = 0, locked = 0, unsold = 0
      
      // API返回 {group: "5", groupData: [{unitId, unitNum, status, ...}]}
      const floors = groups.map(group => {
        const groupData = (group.groupData || []).map(unit => {
          const status = unit.status != null ? unit.status : 1
          const statusStr = STATUS_MAP[status] || 'unsale'
          
          // 统计
          if (status === 2) signed++
          else if (status === 3) locked++
          else unsold++
          
          return {
            unitId: unit.unitId || '',
            unitNum: unit.unitNum || '',
            status: status,
            statusStr: statusStr,
            houseFunction: unit.houseFunction || '',
            totalArea: unit.totalArea || 0,
            inArea: unit.inArea || 0
          }
        })
        
        return {
          group: group.group || '',
          groupData: groupData
        }
      })
      
      this.setData({
        floors,
        loading: false,
        stats: { signed, locked, unsold }
      })
    }).catch(err => {
      console.error('加载单元数据失败:', err)
      this.setData({ loading: false })
    })
  }
})